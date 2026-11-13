"""Stack-Trace, AST Call-Graph & Lexical Spectrum Fault Localizer.

Addresses Context-Window Flooding in autonomous coding agents by deterministically
ranking the top suspect functions/methods from a Python traceback or pytest failure
log and extracting minimal, line-numbered AST slices within a strict token budget.
"""

from __future__ import annotations

import ast
import math
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

_STD_FRAME_RE = re.compile(
    r'^\s*File\s+"([^"]+)",\s+line\s+(\d+),\s+in\s+([^\s\n]+)',
    re.MULTILINE,
)
_PYTEST_FRAME_RE = re.compile(
    r"^([^\s:]+\.py):(\d+):\s+in\s+([^\s\n]+)",
    re.MULTILINE,
)
_PYTEST_SHORT_LOC_RE = re.compile(
    r"^([^\s:]+\.py):(\d+):\s+([A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception|Warning|Failure))(?::\s*(.*))?$",
    re.MULTILINE,
)
_EXCEPTION_LINE_RE = re.compile(
    r"^(?:E\s+)?([A-Za-z_][A-Za-z0-9_.]*(?:Error|Exception|Warning|Exit|Interrupt|Failure))(?::\s*(.+))?$",
    re.MULTILINE,
)
_ASSERT_LINE_RE = re.compile(
    r"^(?:E\s+|>\s+|\s+)(assert\s+.+)$",
    re.MULTILINE,
)
_TEST_HEADER_RE = re.compile(
    r"_{3,}\s+([A-Za-z0-9_.\[\]-]+)\s+_{3,}",
)
_CAMEL_SPLIT_RE = re.compile(r"(?<=[a-z0-9])(?=[A-Z])|[^a-zA-Z0-9]+")

_STOPWORDS = frozenset(
    {
        "the",
        "and",
        "for",
        "with",
        "not",
        "from",
        "that",
        "this",
        "are",
        "was",
        "were",
        "have",
        "has",
        "had",
        "but",
        "self",
        "cls",
        "none",
        "true",
        "false",
        "return",
        "def",
        "class",
        "assert",
        "error",
        "exception",
        "line",
        "file",
        "most",
        "recent",
        "call",
        "last",
        "traceback",
    }
)


def tokenize_identifier_text(text: str) -> list[str]:
    """Split snake_case, camelCase, and free text into normalized lowercase tokens."""
    if not text:
        return []
    raw_parts = _CAMEL_SPLIT_RE.split(text)
    tokens: list[str] = []
    for part in raw_parts:
        for sub in part.lower().split("_"):
            if len(sub) >= 2 and sub not in _STOPWORDS and not sub.isdigit():
                tokens.append(sub)
    return tokens


@dataclass(frozen=True)
class StackFrame:
    """Single stack frame extracted from a Python traceback or pytest failure output."""

    file_path: str
    line_number: int
    function_name: str
    code_line: str = ""
    depth_from_crash: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "file_path": self.file_path,
            "line_number": self.line_number,
            "function_name": self.function_name,
            "code_line": self.code_line,
            "depth_from_crash": self.depth_from_crash,
        }


@dataclass
class TracebackReport:
    """Structured representation of a parsed traceback or pytest failure log."""

    frames: list[StackFrame]
    exception_type: str
    exception_message: str
    violated_assertions: list[str]
    failing_test_name: str = ""
    raw_text: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "frames": [f.to_dict() for f in self.frames],
            "exception_type": self.exception_type,
            "exception_message": self.exception_message,
            "violated_assertions": list(self.violated_assertions),
            "failing_test_name": self.failing_test_name,
        }


@dataclass
class ASTSymbol:
    """Indexed Python AST function, method, or class symbol."""

    symbol_id: str
    name: str
    qualified_name: str
    kind: str  # "function" | "async_function" | "method" | "class"
    file_path: str
    start_line: int
    end_line: int
    docstring: str = ""
    calls: set[str] = field(default_factory=set)
    called_by: set[str] = field(default_factory=set)
    tokens: list[str] = field(default_factory=list)
    source_slice: str = ""

    @property
    def is_test_symbol(self) -> bool:
        base = os.path.basename(self.file_path)
        return (
            base.startswith("test_")
            or base.endswith("_test.py")
            or self.name.startswith("test_")
            or "/tests/" in self.file_path.replace("\\", "/")
            or self.file_path.replace("\\", "/").startswith("tests/")
        )

    @property
    def estimated_tokens(self) -> int:
        # Rough deterministic token estimate: ~4 chars per token
        return max(1, (len(self.source_slice) + 3) // 4)

    def to_dict(self) -> dict[str, Any]:
        return {
            "symbol_id": self.symbol_id,
            "name": self.name,
            "qualified_name": self.qualified_name,
            "kind": self.kind,
            "file_path": self.file_path,
            "start_line": self.start_line,
            "end_line": self.end_line,
            "docstring": self.docstring,
            "calls": sorted(self.calls),
            "called_by": sorted(self.called_by),
            "is_test_symbol": self.is_test_symbol,
            "estimated_tokens": self.estimated_tokens,
        }


@dataclass
class SuspectLocation:
    """Ranked fault-localization candidate with component score breakdown."""

    rank: int
    symbol: ASTSymbol
    score: float
    stack_score: float
    call_graph_score: float
    lexical_score: float
    reasons: list[str]
    code_slice: str
    estimated_tokens: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "rank": self.rank,
            "symbol_id": self.symbol.symbol_id,
            "qualified_name": self.symbol.qualified_name,
            "file_path": self.symbol.file_path,
            "start_line": self.symbol.start_line,
            "end_line": self.symbol.end_line,
            "score": round(self.score, 4),
            "stack_score": round(self.stack_score, 4),
            "call_graph_score": round(self.call_graph_score, 4),
            "lexical_score": round(self.lexical_score, 4),
            "reasons": list(self.reasons),
            "estimated_tokens": self.estimated_tokens,
            "code_slice": self.code_slice,
        }


@dataclass
class LocalizationResult:
    """Output of FaultLocalizer containing ranked suspects and token-budgeted context."""

    traceback: TracebackReport
    suspects: list[SuspectLocation]
    total_symbols_indexed: int
    token_budget: int
    tokens_used: int

    def to_dict(self) -> dict[str, Any]:
        return {
            "traceback": self.traceback.to_dict(),
            "suspects": [s.to_dict() for s in self.suspects],
            "total_symbols_indexed": self.total_symbols_indexed,
            "token_budget": self.token_budget,
            "tokens_used": self.tokens_used,
        }

    def format_context_prompt(self) -> str:
        """Render a compact, token-budgeted markdown context block for a repair agent."""
        lines = [
            "### Fault Localization Summary",
            f"- **Exception**: `{self.traceback.exception_type}: {self.traceback.exception_message}`",
        ]
        if self.traceback.failing_test_name:
            lines.append(f"- **Failing Test**: `{self.traceback.failing_test_name}`")
        if self.traceback.violated_assertions:
            lines.append(
                f"- **Violated Assertion**: `{self.traceback.violated_assertions[-1]}`"
            )
        lines.append(
            f"- **Token Budget**: {self.tokens_used}/{self.token_budget} tokens across {len(self.suspects)} suspect slice(s)"
        )
        lines.append("")
        for suspect in self.suspects:
            lines.append(
                f"#### Suspect #{suspect.rank}: `{suspect.symbol.qualified_name}` "
                f"(`{suspect.symbol.file_path}:{suspect.symbol.start_line}-{suspect.symbol.end_line}`, "
                f"score={suspect.score:.3f})"
            )
            lines.append(f"Reasons: {', '.join(suspect.reasons)}")
            lines.append("```python")
            lines.append(suspect.code_slice)
            lines.append("```")
            lines.append("")
        return "\n".join(lines).strip()


class _SymbolVisitor(ast.NodeVisitor):
    """AST visitor extracting functions, methods, classes, and outgoing call edges."""

    def __init__(self, rel_path: str, source_lines: list[str]) -> None:
        self.rel_path = rel_path
        self.source_lines = source_lines
        self.symbols: list[ASTSymbol] = []
        self._class_stack: list[str] = []

    def _extract_numbered_slice(self, start_line: int, end_line: int) -> str:
        lo = max(1, start_line)
        hi = min(len(self.source_lines), end_line)
        rendered: list[str] = []
        for lineno in range(lo, hi + 1):
            rendered.append(f"{lineno:4d} | {self.source_lines[lineno - 1]}")
        return "\n".join(rendered)

    def _collect_calls_and_tokens(self, node: ast.AST) -> tuple[set[str], list[str]]:
        calls: set[str] = set()
        raw_text_parts: list[str] = []
        for child in ast.walk(node):
            if isinstance(child, ast.Call):
                func = child.func
                if isinstance(func, ast.Name):
                    calls.add(func.id)
                elif isinstance(func, ast.Attribute):
                    calls.add(func.attr)
            elif isinstance(child, ast.Name):
                raw_text_parts.append(child.id)
            elif isinstance(child, ast.Attribute):
                raw_text_parts.append(child.attr)
            elif isinstance(child, ast.Constant) and isinstance(child.value, str):
                raw_text_parts.append(child.value)
        tokens = tokenize_identifier_text(" ".join(raw_text_parts))
        return calls, tokens

    def visit_ClassDef(self, node: ast.ClassDef) -> None:
        start_line = getattr(node, "lineno", 1)
        end_line = getattr(node, "end_lineno", start_line) or start_line
        docstring = ast.get_docstring(node) or ""
        qual = ".".join([*self._class_stack, node.name])
        symbol_id = f"{self.rel_path}::{qual}"
        # Only register the class header + docstring if the class has methods,
        # or full class if small
        header_end = min(end_line, start_line + 15)
        calls, tokens = self._collect_calls_and_tokens(node)
        tokens.extend(tokenize_identifier_text(node.name))
        self.symbols.append(
            ASTSymbol(
                symbol_id=symbol_id,
                name=node.name,
                qualified_name=qual,
                kind="class",
                file_path=self.rel_path,
                start_line=start_line,
                end_line=end_line,
                docstring=docstring,
                calls=calls,
                tokens=tokens,
                source_slice=self._extract_numbered_slice(start_line, header_end),
            )
        )
        self._class_stack.append(node.name)
        self.generic_visit(node)
        self._class_stack.pop()

    def _visit_func(self, node: ast.FunctionDef | ast.AsyncFunctionDef, is_async: bool) -> None:
        start_line = getattr(node, "lineno", 1)
        if node.decorator_list:
            first_dec = getattr(node.decorator_list[0], "lineno", start_line)
            start_line = min(start_line, first_dec)
        end_line = getattr(node, "end_lineno", start_line) or start_line
        docstring = ast.get_docstring(node) or ""
        qual = ".".join([*self._class_stack, node.name])
        kind = "method" if self._class_stack else ("async_function" if is_async else "function")
        symbol_id = f"{self.rel_path}::{qual}"
        calls, tokens = self._collect_calls_and_tokens(node)
        tokens.extend(tokenize_identifier_text(qual))
        tokens.extend(tokenize_identifier_text(self.rel_path))
        for arg in node.args.args:
            tokens.extend(tokenize_identifier_text(arg.arg))
        self.symbols.append(
            ASTSymbol(
                symbol_id=symbol_id,
                name=node.name,
                qualified_name=qual,
                kind=kind,
                file_path=self.rel_path,
                start_line=start_line,
                end_line=end_line,
                docstring=docstring,
                calls=calls,
                tokens=tokens,
                source_slice=self._extract_numbered_slice(start_line, end_line),
            )
        )
        self.generic_visit(node)

    def visit_FunctionDef(self, node: ast.FunctionDef) -> None:
        self._visit_func(node, is_async=False)

    def visit_AsyncFunctionDef(self, node: ast.AsyncFunctionDef) -> None:
        self._visit_func(node, is_async=True)


class ASTSymbolIndex:
    """Workspace-wide AST symbol table and bidirectional call graph."""

    def __init__(self, workspace_root: str | Path | None = None) -> None:
        self.workspace_root = Path(workspace_root).resolve() if workspace_root else None
        self.symbols: dict[str, ASTSymbol] = {}
        self._by_name: dict[str, list[ASTSymbol]] = {}
        self._by_file: dict[str, list[ASTSymbol]] = {}
        self._doc_freq: dict[str, int] = {}
        self._avg_doc_len: float = 1.0

    @classmethod
    def from_directory(
        cls,
        workspace_root: str | Path,
        exclude_dirs: set[str] | None = None,
    ) -> ASTSymbolIndex:
        """Scan all `.py` files under `workspace_root` and build the AST call graph."""
        root = Path(workspace_root).resolve()
        index = cls(workspace_root=root)
        ignored = exclude_dirs or {
            ".git",
            ".venv",
            "venv",
            "__pycache__",
            ".pytest_cache",
            ".ruff_cache",
            "build",
            "dist",
            "node_modules",
        }
        file_map: dict[str, str] = {}
        for dirpath, dirnames, filenames in os.walk(root):
            dirnames[:] = [d for d in sorted(dirnames) if d not in ignored and not d.startswith(".")]
            for fname in sorted(filenames):
                if fname.endswith(".py"):
                    full_path = Path(dirpath) / fname
                    rel_path = full_path.relative_to(root).as_posix()
                    try:
                        file_map[rel_path] = full_path.read_text(encoding="utf-8")
                    except OSError:
                        continue
        index.index_sources(file_map)
        return index

    @classmethod
    def from_sources(cls, sources: dict[str, str]) -> ASTSymbolIndex:
        """Build an index directly from an in-memory `{rel_path: source_code}` mapping."""
        index = cls(workspace_root=None)
        index.index_sources(sources)
        return index

    def index_sources(self, sources: dict[str, str]) -> None:
        """Parse Python sources, populate symbols, and wire caller/callee relationships."""
        for raw_path, code in sorted(sources.items()):
            rel_path = raw_path.replace("\\", "/")
            try:
                tree = ast.parse(code, filename=rel_path)
            except SyntaxError:
                continue
            lines = code.splitlines()
            visitor = _SymbolVisitor(rel_path, lines)
            visitor.visit(tree)
            for sym in visitor.symbols:
                self.symbols[sym.symbol_id] = sym
                self._by_name.setdefault(sym.name, []).append(sym)
                self._by_file.setdefault(rel_path, []).append(sym)

        # Wire bidirectional call-graph edges and compute BM25 statistics
        total_len = 0
        self._doc_freq.clear()
        for sym in self.symbols.values():
            total_len += len(sym.tokens)
            for tok in set(sym.tokens):
                self._doc_freq[tok] = self._doc_freq.get(tok, 0) + 1
            for callee_name in sym.calls:
                for target in self._by_name.get(callee_name, []):
                    if target.symbol_id != sym.symbol_id:
                        target.called_by.add(sym.symbol_id)

        n_docs = max(1, len(self.symbols))
        self._avg_doc_len = max(1.0, total_len / n_docs)

    def normalize_path(self, file_path: str) -> str:
        """Normalize a traceback file path to match indexed relative paths."""
        clean = file_path.replace("\\", "/")
        if clean in self._by_file:
            return clean
        if self.workspace_root:
            try:
                rel = Path(file_path).resolve().relative_to(self.workspace_root).as_posix()
                if rel in self._by_file:
                    return rel
            except (ValueError, OSError):
                pass
        # Suffix match fallback
        for indexed_path in self._by_file:
            if clean.endswith("/" + indexed_path) or indexed_path.endswith("/" + clean) or clean == indexed_path:
                return indexed_path
        return clean

    def find_enclosing_symbol(self, file_path: str, line_number: int) -> ASTSymbol | None:
        """Return the tightest enclosing function/method/class symbol at `(file_path, line_number)`."""
        norm = self.normalize_path(file_path)
        candidates = self._by_file.get(norm, [])
        enclosing: list[ASTSymbol] = [
            s for s in candidates if s.start_line <= line_number <= s.end_line
        ]
        if not enclosing:
            return None
        # Prefer functions/methods over classes, and tighter line spans first
        enclosing.sort(
            key=lambda s: (0 if s.kind != "class" else 1, s.end_line - s.start_line)
        )
        return enclosing[0]

    def find_by_name(self, name: str) -> list[ASTSymbol]:
        """Look up symbols by short name, qualified name, or substring."""
        if name in self._by_name:
            return list(self._by_name[name])
        results: list[ASTSymbol] = []
        q = name.lower()
        for sym in self.symbols.values():
            if q in sym.qualified_name.lower() or q in sym.symbol_id.lower():
                results.append(sym)
        return results

    def bm25_similarity(self, query_tokens: list[str], symbol: ASTSymbol) -> float:
        """Compute normalized BM25 lexical similarity in `[0.0, 1.0]` between query and symbol."""
        if not query_tokens or not symbol.tokens:
            return 0.0
        n_docs = max(1, len(self.symbols))
        k1 = 1.5
        b = 0.75
        doc_len = len(symbol.tokens)
        tf_map: dict[str, int] = {}
        for tok in symbol.tokens:
            tf_map[tok] = tf_map.get(tok, 0) + 1

        raw_score = 0.0
        max_possible = 0.0
        unique_query = list(dict.fromkeys(query_tokens))
        for q_tok in unique_query:
            df = self._doc_freq.get(q_tok, 0)
            idf = math.log(1.0 + (n_docs - df + 0.5) / (df + 0.5))
            max_possible += idf * (k1 + 1.0)
            tf = tf_map.get(q_tok, 0)
            if tf > 0:
                denom = tf + k1 * (1.0 - b + b * (doc_len / self._avg_doc_len))
                raw_score += idf * ((tf * (k1 + 1.0)) / denom)

        if max_possible <= 0.0:
            return 0.0
        return min(1.0, raw_score / max_possible)


def parse_traceback(raw_text: str) -> TracebackReport:
    """Parse standard Python tracebacks and pytest failure outputs into a `TracebackReport`."""
    lines = raw_text.splitlines()
    raw_frames: list[tuple[str, int, str, str]] = []

    # 1. Standard Python traceback frames: File "...", line N, in func
    for match in _STD_FRAME_RE.finditer(raw_text):
        fpath, lineno_str, func_name = match.group(1), match.group(2), match.group(3)
        end_pos = match.end()
        rem = raw_text[end_pos:].splitlines()
        code_line = rem[1].strip() if len(rem) > 1 else ""
        raw_frames.append((fpath, int(lineno_str), func_name, code_line))

    # 2. Pytest style frames: path/to/file.py:42: in func_name
    if not raw_frames:
        for match in _PYTEST_FRAME_RE.finditer(raw_text):
            fpath, lineno_str, func_name = match.group(1), match.group(2), match.group(3)
            end_pos = match.end()
            rem = raw_text[end_pos:].splitlines()
            code_line = ""
            for candidate_line in rem[1:4]:
                stripped = candidate_line.strip()
                if stripped.startswith(">"):
                    code_line = stripped.lstrip(">").strip()
                    break
                if stripped and not stripped.startswith("E "):
                    code_line = stripped
                    break
            raw_frames.append((fpath, int(lineno_str), func_name, code_line))

    # 3. Pytest short location line: path/to/file.py:42: ValueError: message
    short_exc_type = ""
    short_exc_msg = ""
    for match in _PYTEST_SHORT_LOC_RE.finditer(raw_text):
        fpath, lineno_str, exc_name, exc_msg = (
            match.group(1),
            match.group(2),
            match.group(3),
            match.group(4) or "",
        )
        short_exc_type = exc_name
        short_exc_msg = exc_msg.strip()
        if not any(f[0] == fpath and f[1] == int(lineno_str) for f in raw_frames):
            raw_frames.append((fpath, int(lineno_str), "<line>", ""))

    total_frames = len(raw_frames)
    frames: list[StackFrame] = []
    for idx, (fpath, lineno, func_name, code_line) in enumerate(raw_frames):
        depth_from_crash = (total_frames - 1) - idx
        frames.append(
            StackFrame(
                file_path=fpath,
                line_number=lineno,
                function_name=func_name,
                code_line=code_line,
                depth_from_crash=depth_from_crash,
            )
        )

    # Extract exception type and message
    exception_type = short_exc_type or "Exception"
    exception_message = short_exc_msg or ""
    for line in reversed(lines):
        stripped = line.strip()
        m = _EXCEPTION_LINE_RE.match(stripped)
        if m:
            exception_type = m.group(1)
            exception_message = (m.group(2) or "").strip()
            break

    # Extract violated assertions
    violated_assertions: list[str] = []
    for m in _ASSERT_LINE_RE.finditer(raw_text):
        expr = m.group(1).strip()
        if expr not in violated_assertions:
            violated_assertions.append(expr)

    # Extract failing test name from header or test_* frame
    failing_test_name = ""
    header_match = _TEST_HEADER_RE.search(raw_text)
    if header_match:
        failing_test_name = header_match.group(1).strip()
    if not failing_test_name:
        for frame in frames:
            if frame.function_name.startswith("test_"):
                failing_test_name = frame.function_name
                break

    return TracebackReport(
        frames=frames,
        exception_type=exception_type,
        exception_message=exception_message,
        violated_assertions=violated_assertions,
        failing_test_name=failing_test_name,
        raw_text=raw_text,
    )


class FaultLocalizer:
    """Hybrid Stack-Trace + AST Call-Graph + BM25 Spectrum Fault Localizer.

    Combines three complementary signals to rank suspect functions:
    1. **Stack-Frame Depth Proximity (`w_stack=0.55`)**: Functions directly on the crashing
       call stack, weighted exponentially toward the innermost non-test frame (`0.85 ** depth`).
    2. **AST Call-Graph Proximity (`w_graph=0.25`)**: Callees and callers within 1-2 hops of
       any stack-trace symbol or the failing test function (critical when an upstream helper
       returned a corrupted value that triggered an assertion in the caller).
    3. **BM25 Lexical & Identifier Overlap (`w_lexical=0.20`)**: Identifier overlap between
       the exception message, violated assertion expression, failing test name, and AST symbol
       body/signature.
    """

    def __init__(
        self,
        index: ASTSymbolIndex,
        *,
        w_stack: float = 0.55,
        w_graph: float = 0.25,
        w_lexical: float = 0.20,
        demote_test_symbols: bool = True,
    ) -> None:
        self.index = index
        self.w_stack = w_stack
        self.w_graph = w_graph
        self.w_lexical = w_lexical
        self.demote_test_symbols = demote_test_symbols

    @classmethod
    def from_directory(cls, workspace_root: str | Path, **kwargs: Any) -> FaultLocalizer:
        return cls(ASTSymbolIndex.from_directory(workspace_root), **kwargs)

    @classmethod
    def from_sources(cls, sources: dict[str, str], **kwargs: Any) -> FaultLocalizer:
        return cls(ASTSymbolIndex.from_sources(sources), **kwargs)

    def localize(
        self,
        traceback_text: str,
        *,
        top_k: int = 5,
        token_budget: int = 1200,
        include_tests: bool = False,
    ) -> LocalizationResult:
        """Rank suspect AST symbols from `traceback_text` and extract slices within `token_budget`."""
        report = parse_traceback(traceback_text)

        # Map stack frames to AST symbols
        frame_symbols: dict[str, tuple[float, StackFrame]] = {}
        app_frame_order: list[ASTSymbol] = []
        all_frame_symbols: list[ASTSymbol] = []

        for frame in report.frames:
            sym = self.index.find_enclosing_symbol(frame.file_path, frame.line_number)
            if sym is None and frame.function_name and frame.function_name != "<line>":
                by_name = self.index.find_by_name(frame.function_name)
                if len(by_name) == 1:
                    sym = by_name[0]
            if sym is not None:
                all_frame_symbols.append(sym)
                if not sym.is_test_symbol:
                    app_frame_order.append(sym)

        # Compute Stack-Frame Depth Score: innermost application frame gets 1.0
        for idx, sym in enumerate(reversed(app_frame_order)):
            depth_score = 0.85**idx
            prev = frame_symbols.get(sym.symbol_id)
            if prev is None or depth_score > prev[0]:
                matching_frame = next(
                    (
                        f
                        for f in reversed(report.frames)
                        if self.index.find_enclosing_symbol(f.file_path, f.line_number) == sym
                        or f.function_name == sym.name
                    ),
                    report.frames[-1],
                )
                frame_symbols[sym.symbol_id] = (depth_score, matching_frame)

        # Also record test frames with a lower stack score if requested or as call-graph roots
        for sym in all_frame_symbols:
            if sym.symbol_id not in frame_symbols:
                matching_frame = report.frames[-1]
                frame_symbols[sym.symbol_id] = (0.35, matching_frame)

        # Build 1-hop and 2-hop call-graph neighborhood from stack-frame symbols & failing test
        hop1_ids: set[str] = set()
        hop2_ids: set[str] = set()
        seed_symbols: list[ASTSymbol] = list(all_frame_symbols)
        if report.failing_test_name:
            seed_symbols.extend(self.index.find_by_name(report.failing_test_name))

        seed_ids = {s.symbol_id for s in seed_symbols}
        for seed in seed_symbols:
            for callee_name in seed.calls:
                for target in self.index.find_by_name(callee_name):
                    if target.symbol_id not in seed_ids:
                        hop1_ids.add(target.symbol_id)
            for caller_id in seed.called_by:
                if caller_id not in seed_ids:
                    hop1_ids.add(caller_id)

        for h1_id in list(hop1_ids):
            h1_sym = self.index.symbols.get(h1_id)
            if not h1_sym:
                continue
            for callee_name in h1_sym.calls:
                for target in self.index.find_by_name(callee_name):
                    if target.symbol_id not in seed_ids and target.symbol_id not in hop1_ids:
                        hop2_ids.add(target.symbol_id)
            for caller_id in h1_sym.called_by:
                if caller_id not in seed_ids and caller_id not in hop1_ids:
                    hop2_ids.add(caller_id)

        # Build query tokens from exception type/message, assertions, failing test, and frame code lines
        query_parts: list[str] = [
            report.exception_type,
            report.exception_message,
            report.failing_test_name,
            *report.violated_assertions,
            *(f.code_line for f in report.frames),
            *(f.function_name for f in report.frames),
        ]
        query_tokens = tokenize_identifier_text(" ".join(query_parts))

        # Score every non-class symbol (or class if no functions match)
        scored_candidates: list[SuspectLocation] = []
        for sym in self.index.symbols.values():
            if sym.kind == "class":
                continue
            if sym.is_test_symbol and not include_tests:
                continue

            reasons: list[str] = []
            stack_score = 0.0
            graph_score = 0.0

            if sym.symbol_id in frame_symbols:
                stack_score, frame_obj = frame_symbols[sym.symbol_id]
                reasons.append(
                    f"direct stack frame at {sym.file_path}:{frame_obj.line_number}"
                )
                # Direct stack frame symbols also have maximal call-graph proximity (1.0)
                graph_score = 1.0
            elif sym.symbol_id in hop1_ids:
                graph_score = 0.80
                reasons.append("1-hop AST call-graph neighbor of failing frame")
            elif sym.symbol_id in hop2_ids:
                graph_score = 0.45
                reasons.append("2-hop AST call-graph neighbor of failing frame")

            lexical_score = self.index.bm25_similarity(query_tokens, sym)
            if lexical_score >= 0.15:
                reasons.append(f"BM25 token overlap ({lexical_score:.2f})")

            # Bonus if symbol name is explicitly mentioned in violated assertion or exception message
            assertion_blob = " ".join(report.violated_assertions) + " " + report.exception_message
            if re.search(rf"\b{re.escape(sym.name)}\b", assertion_blob):
                graph_score = max(graph_score, 0.90)
                lexical_score = min(1.0, lexical_score + 0.30)
                reasons.append(f"symbol `{sym.name}` referenced in assertion/exception")

            total_score = (
                self.w_stack * stack_score
                + self.w_graph * graph_score
                + self.w_lexical * lexical_score
            )

            if sym.is_test_symbol and self.demote_test_symbols:
                total_score *= 0.35

            if total_score > 0.01:
                scored_candidates.append(
                    SuspectLocation(
                        rank=0,
                        symbol=sym,
                        score=total_score,
                        stack_score=stack_score,
                        call_graph_score=graph_score,
                        lexical_score=lexical_score,
                        reasons=reasons or ["lexical similarity"],
                        code_slice=sym.source_slice,
                        estimated_tokens=sym.estimated_tokens,
                    )
                )

        scored_candidates.sort(
            key=lambda c: (
                -c.score,
                -c.stack_score,
                -c.call_graph_score,
                -c.lexical_score,
                c.symbol.symbol_id,
            )
        )

        # Enforce both top_k and token_budget
        selected: list[SuspectLocation] = []
        tokens_used = 0
        for cand in scored_candidates:
            if len(selected) >= top_k:
                break
            if tokens_used + cand.estimated_tokens > token_budget and selected:
                continue
            cand.rank = len(selected) + 1
            selected.append(cand)
            tokens_used += cand.estimated_tokens

        return LocalizationResult(
            traceback=report,
            suspects=selected,
            total_symbols_indexed=len(self.index.symbols),
            token_budget=token_budget,
            tokens_used=tokens_used,
        )

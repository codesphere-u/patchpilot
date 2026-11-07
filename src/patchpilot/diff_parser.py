"""Unified Diff Parser and Multi-File Batch AST Auditor.

Allows PatchPilot to parse git unified diff strings (e.g. from `git diff`,
GitHub PR patches, or agent patch outputs) across multiple files and evaluate
`RH001`–`RH008` rules with or without requiring the original repository files.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass, field
from typing import Any

from patchpilot.guard import (
    DiffStats,
    GuardViolation,
    PatchIntegrityGuard,
    PatchVerdict,
    apply_unified_diff_to_map,
    build_unified_diff,
)

_DIFF_HEADER_RE = re.compile(r"^diff --git a/(.+?) b/(.+?)$", re.MULTILINE)
_ORIG_FILE_RE = re.compile(r"^---\s+(?:[ab]/)?(.+?)(?:\t.*)?$", re.MULTILINE)
_NEW_FILE_RE = re.compile(r"^\+\+\+\s+(?:[ab]/)?(.+?)(?:\t.*)?$", re.MULTILINE)
_HUNK_RE = re.compile(r"^@@ -(\d+)(?:,(\d+))? \+(\d+)(?:,(\d+))? @@(.*)$")


@dataclass(frozen=True)
class FilePatchHunk:
    """A single unified diff hunk (@@ -l,s +l,s @@)."""

    old_start: int
    old_count: int
    new_start: int
    new_count: int
    heading: str
    lines: list[str]


@dataclass
class FileDiff:
    """The collection of hunks and metadata for a single file in a unified diff."""

    old_path: str
    new_path: str
    hunks: list[FilePatchHunk] = field(default_factory=list)
    is_new: bool = False
    is_deleted: bool = False


@dataclass
class ParsedDiff:
    """Structured representation of a multi-file unified diff."""

    files: list[FileDiff]
    raw_diff: str

    @property
    def file_paths(self) -> list[str]:
        paths = []
        for f in self.files:
            p = f.new_path if f.new_path != "/dev/null" else f.old_path
            if p and p not in paths:
                paths.append(p)
        return paths


def parse_unified_diff(diff_text: str) -> ParsedDiff:
    """Parse a multi-file unified git diff into structured `FileDiff` records."""
    file_diffs: list[FileDiff] = []
    current_file: FileDiff | None = None
    current_hunk_lines: list[str] = []
    current_hunk_meta: tuple[int, int, int, int, str] | None = None

    def _flush_hunk() -> None:
        nonlocal current_hunk_lines, current_hunk_meta
        if current_file and current_hunk_meta:
            old_s, old_c, new_s, new_c, heading = current_hunk_meta
            current_file.hunks.append(
                FilePatchHunk(
                    old_start=old_s,
                    old_count=old_c,
                    new_start=new_s,
                    new_count=new_c,
                    heading=heading,
                    lines=list(current_hunk_lines),
                )
            )
        current_hunk_lines = []
        current_hunk_meta = None

    for raw_line in diff_text.splitlines():
        # Clean diff lines
        line = raw_line.rstrip("\r\n")

        if line.startswith("diff --git "):
            _flush_hunk()
            m = _DIFF_HEADER_RE.match(line)
            if m:
                old_p, new_p = m.group(1), m.group(2)
            else:
                parts = line.split()
                old_p = parts[2].removeprefix("a/") if len(parts) > 2 else "unknown"
                new_p = parts[3].removeprefix("b/") if len(parts) > 3 else old_p
            current_file = FileDiff(old_path=old_p, new_path=new_p)
            file_diffs.append(current_file)
            continue

        if line.startswith("--- "):
            m = _ORIG_FILE_RE.match(line)
            if m:
                orig_path = m.group(1).strip()
                if orig_path == "/dev/null" and current_file:
                    current_file.is_new = True
                elif current_file and (not current_file.old_path or current_file.old_path == "unknown"):
                    current_file.old_path = orig_path
            continue

        if line.startswith("+++ "):
            m = _NEW_FILE_RE.match(line)
            if m:
                new_path = m.group(1).strip()
                if new_path == "/dev/null" and current_file:
                    current_file.is_deleted = True
                elif current_file and (not current_file.new_path or current_file.new_path == "unknown"):
                    current_file.new_path = new_path
            continue

        hm = _HUNK_RE.match(line)
        if hm:
            _flush_hunk()
            old_s = int(hm.group(1))
            old_c = int(hm.group(2)) if hm.group(2) is not None else 1
            new_s = int(hm.group(3))
            new_c = int(hm.group(4)) if hm.group(4) is not None else 1
            heading = hm.group(5).strip()
            current_hunk_meta = (old_s, old_c, new_s, new_c, heading)
            continue

        if current_hunk_meta is not None:
            if line.startswith(("+", "-", " ", "\\")):
                current_hunk_lines.append(line)

    _flush_hunk()
    return ParsedDiff(files=file_diffs, raw_diff=diff_text)


def reconstruct_file_pairs_from_diff(diff_text: str) -> tuple[dict[str, str], dict[str, str]]:
    """
    Reconstruct synthetic before and after file sources from hunk additions and deletions.

    Useful when auditing a pull request patch where the full repository source files
    are not available locally.
    """
    parsed = parse_unified_diff(diff_text)
    before_map: dict[str, str] = {}
    after_map: dict[str, str] = {}

    for f in parsed.files:
        path = f.new_path if f.new_path != "/dev/null" else f.old_path
        if not path or path == "unknown":
            continue

        before_lines: list[str] = []
        after_lines: list[str] = []

        for hunk in f.hunks:
            for l in hunk.lines:
                if l.startswith(" "):
                    before_lines.append(l[1:])
                    after_lines.append(l[1:])
                elif l.startswith("-"):
                    before_lines.append(l[1:])
                elif l.startswith("+"):
                    after_lines.append(l[1:])

        before_map[path] = "\n".join(before_lines) + ("\n" if before_lines else "")
        after_map[path] = "\n".join(after_lines) + ("\n" if after_lines else "")

    return before_map, after_map


@dataclass
class UnifiedDiffAuditReport:
    """Comprehensive audit report produced by evaluating a raw unified git diff."""

    approved: bool
    risk_score: float
    violations: list[GuardViolation]
    diff_stats: DiffStats
    sha256_diff_id: str
    file_paths: list[str]
    raw_diff: str

    def to_dict(self) -> dict[str, Any]:
        return {
            "approved": self.approved,
            "risk_score": round(self.risk_score, 4),
            "sha256_diff_id": self.sha256_diff_id,
            "file_paths": self.file_paths,
            "diff_stats": self.diff_stats.to_dict(),
            "violations": [v.to_dict() for v in self.violations],
        }


def audit_unified_diff(
    diff_text: str,
    original_files: dict[str, str] | None = None,
    guard: PatchIntegrityGuard | None = None,
) -> UnifiedDiffAuditReport:
    """
    Audit a raw multi-file unified git diff against RH001–RH008 rules.

    If `original_files` is provided, the diff is applied directly against the full files.
    Otherwise, synthetic before and after ASTs are reconstructed from context and delta lines.
    """
    g = guard or PatchIntegrityGuard()
    sha256_id = hashlib.sha256(diff_text.encode("utf-8")).hexdigest()

    if original_files is not None:
        verdict = g.verify_diff(original_files, diff_text)
        return UnifiedDiffAuditReport(
            approved=verdict.approved,
            risk_score=verdict.risk_score,
            violations=verdict.violations,
            diff_stats=verdict.diff_stats,
            sha256_diff_id=verdict.sha256_patch_id,
            file_paths=verdict.diff_stats.touched_paths,
            raw_diff=diff_text,
        )

    # Reconstruct from hunk lines
    before_map, after_map = reconstruct_file_pairs_from_diff(diff_text)
    verdict = g.verify_files(before_map, after_map)
    return UnifiedDiffAuditReport(
        approved=verdict.approved,
        risk_score=verdict.risk_score,
        violations=verdict.violations,
        diff_stats=verdict.diff_stats,
        sha256_diff_id=sha256_id,
        file_paths=list(after_map.keys()),
        raw_diff=diff_text,
    )

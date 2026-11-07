"""Model Context Protocol (MCP) JSON-RPC 2.0 Server (`PatchPilotMCPServer`).

Exposes deterministic fault localization, AST anti-reward-hacking verification,
transactional patch application, and AST symbol inspection over JSON-RPC 2.0.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TextIO

from patchpilot.guard import PatchIntegrityGuard
from patchpilot.localizer import ASTSymbolIndex, FaultLocalizer
from patchpilot.sandbox import TransactionalPatchWorkspace

MCP_PROTOCOL_VERSION = "2024-11-05"

MCP_TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "name": "localize_fault",
        "description": (
            "Rank suspect Python functions/methods from a traceback or pytest failure log "
            "using hybrid Stack-Trace + AST Call-Graph + BM25 token overlap, returning "
            "minimal line-numbered AST slices within a strict token budget."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_root": {
                    "type": "string",
                    "description": "Path to the workspace directory containing Python files.",
                },
                "sources": {
                    "type": "object",
                    "description": "Optional in-memory {rel_path: source_code} map instead of workspace_root.",
                },
                "traceback_text": {
                    "type": "string",
                    "description": "Raw Python traceback or pytest failure output.",
                },
                "top_k": {
                    "type": "integer",
                    "default": 5,
                    "description": "Maximum number of suspect functions to return.",
                },
                "token_budget": {
                    "type": "integer",
                    "default": 1200,
                    "description": "Maximum token budget across returned AST code slices.",
                },
                "include_tests": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to include test_* functions in ranked candidates.",
                },
            },
            "required": ["traceback_text"],
        },
    },
    {
        "name": "verify_patch_integrity",
        "description": (
            "Evaluate a proposed patch (original vs patched files or unified diff) against "
            "8 deterministic AST anti-reward-hacking & safety rules (RH001–RH008)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "original_files": {
                    "type": "object",
                    "description": "Mapping of {rel_path: original_source_code}.",
                },
                "patched_files": {
                    "type": "object",
                    "description": "Mapping of {rel_path: patched_source_code}.",
                },
                "unified_diff": {
                    "type": "string",
                    "description": "Optional unified diff string applied onto original_files.",
                },
                "max_files_touched": {
                    "type": "integer",
                    "default": 5,
                },
                "max_lines_changed": {
                    "type": "integer",
                    "default": 250,
                },
                "allow_test_modifications": {
                    "type": "boolean",
                    "default": False,
                },
            },
            "required": ["original_files"],
        },
    },
    {
        "name": "apply_transactional_patch",
        "description": (
            "Apply a candidate patch inside a snapshot-backed workspace transaction, "
            "verifying RH001–RH008 and running an optional test command with automatic "
            "byte-exact SHA-256 rollback on failure."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_root": {
                    "type": "string",
                    "description": "Workspace directory path.",
                },
                "patched_files": {
                    "type": "object",
                    "description": "Mapping of {rel_path: new_source_code}.",
                },
                "unified_diff": {
                    "type": "string",
                    "description": "Optional unified diff string.",
                },
                "test_command": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional command list (e.g. ['pytest', '-q']) to verify the patch.",
                },
                "suspects_considered": {
                    "type": "array",
                    "items": {"type": "string"},
                },
            },
            "required": ["workspace_root"],
        },
    },
    {
        "name": "inspect_ast_symbols",
        "description": (
            "Query the AST symbol table and bidirectional call graph of a workspace by "
            "symbol name or (file_path, line_number)."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "workspace_root": {
                    "type": "string",
                    "description": "Workspace directory path.",
                },
                "sources": {
                    "type": "object",
                    "description": "Optional in-memory {rel_path: source_code} map.",
                },
                "query_name": {
                    "type": "string",
                    "description": "Function, method, or class name to look up.",
                },
                "file_path": {
                    "type": "string",
                    "description": "Relative file path for line-based enclosing symbol lookup.",
                },
                "line_number": {
                    "type": "integer",
                    "description": "1-based line number for enclosing symbol lookup.",
                },
            },
        },
    },
]


class PatchPilotMCPServer:
    """JSON-RPC 2.0 MCP Server for autonomous code repair & anti-reward-hacking verification."""

    def __init__(self, default_workspace: str | Path | None = None) -> None:
        self.default_workspace = Path(default_workspace).resolve() if default_workspace else None

    def handle_request(self, request: dict[str, Any]) -> dict[str, Any] | None:
        """Process a single JSON-RPC 2.0 request dictionary and return a response dict."""
        req_id = request.get("id")
        method = request.get("method", "")
        params = request.get("params") or {}

        # Notifications have no id and expect no response
        if req_id is None and method.startswith("notifications/"):
            return None

        try:
            if method == "initialize":
                result = {
                    "protocolVersion": MCP_PROTOCOL_VERSION,
                    "serverInfo": {
                        "name": "patchpilot-mcp",
                        "version": "1.0.0",
                    },
                    "capabilities": {
                        "tools": {"listChanged": False},
                    },
                }
                return self._ok(req_id, result)

            if method == "ping":
                return self._ok(req_id, {})

            if method == "tools/list":
                return self._ok(req_id, {"tools": MCP_TOOLS_SCHEMA})

            if method == "tools/call":
                tool_name = params.get("name", "")
                arguments = params.get("arguments") or {}
                payload = self._dispatch_tool(tool_name, arguments)
                return self._ok(
                    req_id,
                    {
                        "content": [
                            {
                                "type": "text",
                                "text": json.dumps(payload, indent=2),
                            }
                        ],
                        "structuredContent": payload,
                        "isError": False,
                    },
                )

            return self._error(req_id, -32601, f"Method not found: {method}")
        except KeyError as exc:
            return self._error(req_id, -32602, f"Missing required parameter: {exc}")
        except ValueError as exc:
            return self._error(req_id, -32602, str(exc))
        except Exception as exc:
            return self._error(req_id, -32603, f"Internal error: {exc}")

    def _dispatch_tool(self, tool_name: str, args: dict[str, Any]) -> dict[str, Any]:
        if tool_name == "localize_fault":
            traceback_text = args["traceback_text"]
            sources = args.get("sources")
            workspace_root = args.get("workspace_root") or self.default_workspace
            if sources is not None:
                localizer = FaultLocalizer.from_sources(sources)
            elif workspace_root is not None:
                localizer = FaultLocalizer.from_directory(workspace_root)
            else:
                raise ValueError("Provide either 'workspace_root' or 'sources'.")
            res = localizer.localize(
                traceback_text,
                top_k=int(args.get("top_k", 5)),
                token_budget=int(args.get("token_budget", 1200)),
                include_tests=bool(args.get("include_tests", False)),
            )
            out = res.to_dict()
            out["formatted_prompt"] = res.format_context_prompt()
            return out

        if tool_name == "verify_patch_integrity":
            original_files = args["original_files"]
            patched_files = args.get("patched_files")
            unified_diff = args.get("unified_diff")
            guard = PatchIntegrityGuard(
                max_files_touched=int(args.get("max_files_touched", 5)),
                max_lines_changed=int(args.get("max_lines_changed", 250)),
                allow_test_modifications=bool(args.get("allow_test_modifications", False)),
            )
            if unified_diff is not None:
                verdict = guard.verify_diff(original_files, unified_diff)
            elif patched_files is not None:
                verdict = guard.verify_files(original_files, patched_files)
            else:
                raise ValueError("Provide either 'patched_files' or 'unified_diff'.")
            return verdict.to_dict()

        if tool_name == "apply_transactional_patch":
            workspace_root = args.get("workspace_root") or self.default_workspace
            if workspace_root is None:
                raise ValueError("'workspace_root' is required.")
            sandbox = TransactionalPatchWorkspace(workspace_root)
            receipt = sandbox.apply_patch_transaction(
                patched_files=args.get("patched_files"),
                unified_diff=args.get("unified_diff"),
                test_command=args.get("test_command"),
                suspects_considered=args.get("suspects_considered"),
            )
            return receipt.to_dict()

        if tool_name == "inspect_ast_symbols":
            sources = args.get("sources")
            workspace_root = args.get("workspace_root") or self.default_workspace
            if sources is not None:
                index = ASTSymbolIndex.from_sources(sources)
            elif workspace_root is not None:
                index = ASTSymbolIndex.from_directory(workspace_root)
            else:
                raise ValueError("Provide either 'workspace_root' or 'sources'.")

            file_path = args.get("file_path")
            line_number = args.get("line_number")
            query_name = args.get("query_name")

            if file_path and line_number is not None:
                sym = index.find_enclosing_symbol(file_path, int(line_number))
                matches = [sym.to_dict()] if sym else []
            elif query_name:
                matches = [s.to_dict() for s in index.find_by_name(query_name)]
            else:
                matches = [s.to_dict() for s in index.symbols.values()]

            return {
                "total_indexed": len(index.symbols),
                "matches": matches,
            }

        raise ValueError(f"Unknown tool: {tool_name}")

    @staticmethod
    def _ok(req_id: Any, result: dict[str, Any]) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "result": result,
        }

    @staticmethod
    def _error(req_id: Any, code: int, message: str) -> dict[str, Any]:
        return {
            "jsonrpc": "2.0",
            "id": req_id,
            "error": {
                "code": code,
                "message": message,
            },
        }

    def serve_stdio(
        self,
        stdin: TextIO = sys.stdin,
        stdout: TextIO = sys.stdout,
    ) -> None:
        """Run the MCP JSON-RPC 2.0 server loop over line-delimited stdio."""
        for raw_line in stdin:
            line = raw_line.strip()
            if not line:
                continue
            try:
                request = json.loads(line)
            except json.JSONDecodeError as exc:
                err = self._error(None, -32700, f"Parse error: {exc}")
                stdout.write(json.dumps(err) + "\n")
                stdout.flush()
                continue

            response = self.handle_request(request)
            if response is not None:
                stdout.write(json.dumps(response) + "\n")
                stdout.flush()

"""Model Context Protocol (MCP) JSON-RPC 2.0 Server (`PatchPilotMCPServer`).

Exposes deterministic fault localization, AST anti-reward-hacking verification,
transactional patch application, and AST symbol inspection over JSON-RPC 2.0.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, TextIO

from patchpilot.guard import PatchIntegrityGuard, RULE_DESCRIPTIONS, RULE_SEVERITY_WEIGHTS
from patchpilot.localizer import ASTSymbolIndex, FaultLocalizer
from patchpilot.sandbox import TransactionalPatchWorkspace

MCP_PROTOCOL_VERSION = "2024-11-05"

MCP_TOOLS_SCHEMA: list[dict[str, Any]] = [
    {
        "name": "audit_unified_diff",
        "description": (
            "Parse and audit a multi-file unified git diff against 8 deterministic AST "
            "anti-reward-hacking & safety rules (RH001–RH008) and export canonical Nexus Aegis G5 leaf attestation."
        ),
        "inputSchema": {
            "type": "object",
            "properties": {
                "unified_diff": {
                    "type": "string",
                    "description": "Multi-file unified diff string (e.g. git diff output).",
                },
                "original_files": {
                    "type": "object",
                    "description": "Optional mapping of {rel_path: original_source_code}.",
                },
                "export_aegis": {
                    "type": "boolean",
                    "default": False,
                    "description": "Whether to include canonical Nexus Aegis G5 attestation package in output.",
                },
            },
            "required": ["unified_diff"],
        },
    },
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

MCP_RESOURCES_SCHEMA: list[dict[str, Any]] = [
    {
        "uri": "patchpilot://rules/catalog",
        "name": "AST Anti-Reward-Hacking Rule Catalog (RH001-RH008)",
        "description": "Deterministic AST safety and anti-reward-hacking rules preventing LLM coding agents from deleting tests, adding trivial assertions, or stubbing functions.",
        "mimeType": "application/json",
    },
    {
        "uri": "patchpilot://stats/overview",
        "name": "PatchPilot Engine Capabilities & AST Specs",
        "description": "Overview of supported Python AST node visitors, fault localization algorithms (Stack-Trace + AST Call-Graph + BM25), and snapshot sandbox guarantees.",
        "mimeType": "application/json",
    },
]

MCP_PROMPTS_SCHEMA: list[dict[str, Any]] = [
    {
        "name": "diagnose-and-repair",
        "description": "Localize the root-cause function from a pytest failure traceback and inspect suspect AST slices within a strict token budget.",
        "arguments": [
            {
                "name": "traceback_text",
                "description": "Raw Python traceback or pytest failure log.",
                "required": True,
            },
            {
                "name": "suspect_file",
                "description": "Optional relative path of the file suspected to contain the bug.",
                "required": False,
            },
        ],
    },
    {
        "name": "audit-git-diff",
        "description": "Audit a unified git diff against RH001-RH008 rules to ensure no test deletion, artificial pass shortcuts, or stubbed functions.",
        "arguments": [
            {
                "name": "unified_diff",
                "description": "Multi-file unified git diff string.",
                "required": True,
            },
        ],
    },
]


class PatchPilotMCPServer:
    """JSON-RPC 2.0 MCP Server for autonomous code repair & anti-reward-hacking verification."""

    def __init__(self, default_workspace: str | Path | None = None) -> None:
        self.default_workspace = Path(default_workspace).resolve() if default_workspace else None

    def get_resource_definitions(self) -> list[dict[str, Any]]:
        return list(MCP_RESOURCES_SCHEMA)

    def get_prompt_definitions(self) -> list[dict[str, Any]]:
        return list(MCP_PROMPTS_SCHEMA)

    def _read_resource(self, uri: str) -> dict[str, Any]:
        if uri == "patchpilot://rules/catalog":
            rules_list = []
            for code, desc in sorted(RULE_DESCRIPTIONS.items()):
                rules_list.append({
                    "code": code,
                    "description": desc,
                    "severity_weight": RULE_SEVERITY_WEIGHTS.get(code, 0.5),
                })
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps({"total_rules": len(rules_list), "rules": rules_list}, indent=2),
                    }
                ]
            }
        if uri == "patchpilot://stats/overview":
            return {
                "contents": [
                    {
                        "uri": uri,
                        "mimeType": "application/json",
                        "text": json.dumps(
                            {
                                "server": "patchpilot-mcp",
                                "version": "1.1.0",
                                "ast_anti_reward_hacking_rules": 8,
                                "fault_localization_algorithms": ["Stack-Trace Parsing", "AST Bidirectional Call Graph", "BM25 Token Overlap"],
                                "safety_guarantees": ["Byte-exact SHA-256 Rollback", "Anti-Reward-Hacking G5 Attestation"],
                            },
                            indent=2,
                        ),
                    }
                ]
            }
        raise KeyError(f"Unknown resource URI: {uri}")

    def _get_prompt(self, name: str, arguments: dict[str, Any] | None) -> dict[str, Any]:
        args = arguments or {}
        if name == "diagnose-and-repair":
            tb = args.get("traceback_text", "")
            sf = args.get("suspect_file", "Not specified")
            return {
                "description": "Guided root cause diagnosis and patch generation",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                "You are an autonomous program repair agent.\n"
                                f"Suspect File: {sf}\n\n"
                                f"Failure Traceback:\n{tb}\n\n"
                                "1. Call `localize_fault` to retrieve minimal line-numbered AST slices.\n"
                                "2. Formulate a minimal, non-cheating patch.\n"
                                "3. Verify with `verify_patch_integrity` to ensure RH001-RH008 compliance."
                            ),
                        },
                    }
                ],
            }
        if name == "audit-git-diff":
            diff = args.get("unified_diff", "")
            return {
                "description": "Audit candidate git diff against RH001-RH008 anti-reward-hacking rules",
                "messages": [
                    {
                        "role": "user",
                        "content": {
                            "type": "text",
                            "text": (
                                "Audit this proposed git diff for RH001-RH008 reward-hacking or test cheating:\n\n"
                                f"```diff\n{diff}\n```\n\n"
                                "Check:\n"
                                "- RH001: Were test files modified without permission?\n"
                                "- RH002: Was an assertion changed to 'assert True'?\n"
                                "- RH003: Are functions returning dummy literals without executing logic?\n"
                                "Provide a pass/fail verdict."
                            ),
                        },
                    }
                ],
            }
        raise KeyError(f"Unknown prompt: {name}")

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
                        "version": "1.1.0",
                    },
                    "capabilities": {
                        "tools": {"listChanged": False},
                        "resources": {"subscribe": False, "listChanged": False},
                        "prompts": {"listChanged": False},
                    },
                }
                return self._ok(req_id, result)

            if method == "ping":
                return self._ok(req_id, {})

            if method == "tools/list":
                return self._ok(req_id, {"tools": MCP_TOOLS_SCHEMA})

            if method == "resources/list":
                return self._ok(req_id, {"resources": self.get_resource_definitions()})

            if method == "resources/read":
                uri = params.get("uri")
                if not uri or not isinstance(uri, str):
                    return self._error(req_id, -32602, "Missing 'uri' parameter.")
                return self._ok(req_id, self._read_resource(uri))

            if method == "prompts/list":
                return self._ok(req_id, {"prompts": self.get_prompt_definitions()})

            if method == "prompts/get":
                prompt_name = params.get("name")
                prompt_args = params.get("arguments")
                if not prompt_name or not isinstance(prompt_name, str):
                    return self._error(req_id, -32602, "Missing prompt 'name'.")
                return self._ok(req_id, self._get_prompt(prompt_name, prompt_args))

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
        if tool_name == "audit_unified_diff":
            from patchpilot.aegis_bridge import create_aegis_g5_leaf
            from patchpilot.diff_parser import audit_unified_diff

            diff_text = args["unified_diff"]
            original_files = args.get("original_files")
            report = audit_unified_diff(diff_text, original_files=original_files)
            res = report.to_dict()
            if args.get("export_aegis", False):
                res["aegis_g5_leaf"] = create_aegis_g5_leaf(report)
            return res

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

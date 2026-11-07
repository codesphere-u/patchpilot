"""Integration tests for `patchpilot.server` (JSON-RPC 2.0 MCP Server) and `patchpilot.cli`."""

from __future__ import annotations

import io
import json
from pathlib import Path

from patchpilot.cli import main
from patchpilot.server import PatchPilotMCPServer


def test_mcp_initialize_ping_and_tools_list():
    server = PatchPilotMCPServer()

    init_resp = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    assert init_resp is not None
    assert init_resp["result"]["serverInfo"]["name"] == "patchpilot-mcp"

    # Notification returns None
    notif_resp = server.handle_request({"jsonrpc": "2.0", "method": "notifications/initialized"})
    assert notif_resp is None

    ping_resp = server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "ping"})
    assert ping_resp == {"jsonrpc": "2.0", "id": 2, "result": {}}

    list_resp = server.handle_request({"jsonrpc": "2.0", "id": 3, "method": "tools/list"})
    assert list_resp is not None
    tool_names = {t["name"] for t in list_resp["result"]["tools"]}
    assert tool_names == {
        "localize_fault",
        "verify_patch_integrity",
        "apply_transactional_patch",
        "inspect_ast_symbols",
    }


def test_mcp_tool_call_localize_fault_and_inspect_symbols():
    server = PatchPilotMCPServer()
    sources = {
        "billing/calc.py": (
            "def compute_vat(net: int) -> int:\n"
            "    return round(net * 0.2)\n\n"
            "def invoice_gross(net: int) -> int:\n"
            "    return net + compute_vat(net)\n"
        )
    }
    tb = (
        '  File "billing/calc.py", line 5, in invoice_gross\n'
        "    return net + compute_vat(net)\n"
        '  File "billing/calc.py", line 2, in compute_vat\n'
        "    return round(net * 0.2)\n"
        "TypeError: unsupported operand type(s)\n"
    )
    resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 10,
            "method": "tools/call",
            "params": {
                "name": "localize_fault",
                "arguments": {
                    "sources": sources,
                    "traceback_text": tb,
                    "top_k": 2,
                },
            },
        }
    )
    assert resp is not None
    structured = resp["result"]["structuredContent"]
    assert structured["suspects"][0]["symbol_id"] == "billing/calc.py::compute_vat"

    inspect_resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 11,
            "method": "tools/call",
            "params": {
                "name": "inspect_ast_symbols",
                "arguments": {
                    "sources": sources,
                    "file_path": "billing/calc.py",
                    "line_number": 2,
                },
            },
        }
    )
    assert inspect_resp is not None
    matches = inspect_resp["result"]["structuredContent"]["matches"]
    assert len(matches) == 1
    assert matches[0]["name"] == "compute_vat"


def test_mcp_tool_call_verify_patch_and_transactional_patch(tmp_path: Path):
    (tmp_path / "app.py").write_text("def double(x: int) -> int:\n    return x + 1\n", encoding="utf-8")
    (tmp_path / "test_app.py").write_text(
        "from app import double\ndef test_double():\n    assert double(4) == 8\n",
        encoding="utf-8",
    )
    server = PatchPilotMCPServer(default_workspace=tmp_path)

    # 1. Verify reward-hacking patch via MCP
    verify_resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 20,
            "method": "tools/call",
            "params": {
                "name": "verify_patch_integrity",
                "arguments": {
                    "original_files": {"test_app.py": "def test_double():\n    assert double(4) == 8\n"},
                    "patched_files": {"test_app.py": "def test_double():\n    assert True\n"},
                },
            },
        }
    )
    assert verify_resp is not None
    verdict = verify_resp["result"]["structuredContent"]
    assert verdict["approved"] is False
    assert any(v["rule_id"] == "RH002" for v in verdict["violations"])

    # 2. Apply valid patch via MCP
    tx_resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 21,
            "method": "tools/call",
            "params": {
                "name": "apply_transactional_patch",
                "arguments": {
                    "workspace_root": str(tmp_path),
                    "patched_files": {"app.py": "def double(x: int) -> int:\n    return x * 2\n"},
                },
            },
        }
    )
    assert tx_resp is not None
    receipt = tx_resp["result"]["structuredContent"]
    assert receipt["status"] == "committed"


def test_mcp_error_handling_and_stdio_loop():
    server = PatchPilotMCPServer()
    unknown_method = server.handle_request({"jsonrpc": "2.0", "id": 99, "method": "nonexistent/method"})
    assert unknown_method is not None
    assert unknown_method["error"]["code"] == -32601

    stdin = io.StringIO(
        '{"jsonrpc": "2.0", "id": 1, "method": "ping"}\n'
        "not-valid-json\n"
    )
    stdout = io.StringIO()
    server.serve_stdio(stdin=stdin, stdout=stdout)
    out_lines = [json.loads(line) for line in stdout.getvalue().strip().splitlines()]
    assert len(out_lines) == 2
    assert out_lines[0]["result"] == {}
    assert out_lines[1]["error"]["code"] == -32700


def test_cli_demo_and_benchmark_json(capsys):
    rc_demo = main(["demo", "--json"])
    assert rc_demo == 0
    demo_out = json.loads(capsys.readouterr().out)
    assert demo_out["reward_hacking_attempt"]["status"] == "rolled_back"
    assert demo_out["genuine_repair"]["status"] == "committed"
    assert demo_out["receipt_integrity_verified"] is True

    rc_bench = main(["benchmark", "--json"])
    assert rc_bench == 0
    bench_out = json.loads(capsys.readouterr().out)
    assert bench_out["fault_localization"]["top1_accuracy"] == 100.0
    assert bench_out["reward_hacking_guard"]["recall_pct"] == 100.0
    assert bench_out["reward_hacking_guard"]["false_positive_rate_pct"] == 0.0

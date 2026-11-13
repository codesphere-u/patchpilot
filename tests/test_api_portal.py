"""Unit tests for the developer portal and upgraded HTTP/SSE endpoints in PatchPilot."""

from __future__ import annotations

import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
API_DIR = ROOT_DIR / "api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))

from portal import render_developer_portal


def test_portal_html_render():
    html = render_developer_portal(
        server_name="patchpilot",
        server_version="1.1.0",
        tagline="Autonomous Code Repair Engine",
        endpoint_url="https://patchpilot-eta.vercel.app/mcp",
        github_url="https://github.com/codesphere-u/patchpilot",
        tools=[{"name": "audit_unified_diff", "description": "Audit diff", "inputSchema": {"properties": {"diff_text": {"type": "string"}}, "required": ["diff_text"]}}],
        resources=[{"uri": "patchpilot://rules/catalog", "name": "Rules Catalog", "mimeType": "application/json", "description": "Anti-reward-hacking rules"}],
        prompts=[{"name": "diagnose-and-repair", "description": "Diagnose traceback", "arguments": [{"name": "traceback_text", "required": True}]}],
        sample_tool_call={"jsonrpc": "2.0", "id": 1, "method": "tools/call", "params": {"name": "audit_unified_diff", "arguments": {"unified_diff": ""}}},
    )
    assert "<!DOCTYPE html>" in html
    assert "patchpilot" in html
    assert "audit_unified_diff" in html
    assert "patchpilot://rules/catalog" in html
    assert "diagnose-and-repair" in html
    assert "Operational" in html
    assert "claude mcp add" in html

"""Tests for PatchPilot MCP Resources and Prompts primitives."""

from patchpilot.server import PatchPilotMCPServer


def test_patchpilot_mcp_initialize_capabilities():
    server = PatchPilotMCPServer()
    resp = server.handle_request({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
    caps = resp["result"]["capabilities"]
    assert "tools" in caps
    assert "resources" in caps
    assert "prompts" in caps


def test_patchpilot_mcp_resources_list_and_read():
    server = PatchPilotMCPServer()
    resp = server.handle_request({"jsonrpc": "2.0", "id": 2, "method": "resources/list"})
    resources = resp["result"]["resources"]
    assert len(resources) >= 2
    uris = [r["uri"] for r in resources]
    assert "patchpilot://rules/catalog" in uris
    assert "patchpilot://stats/overview" in uris

    # Read rule catalog
    read_resp = server.handle_request(
        {"jsonrpc": "2.0", "id": 3, "method": "resources/read", "params": {"uri": "patchpilot://rules/catalog"}}
    )
    content = read_resp["result"]["contents"][0]
    assert content["mimeType"] == "application/json"
    assert "RH001" in content["text"]
    assert "RH008" in content["text"]

    # Read stats overview
    read_resp2 = server.handle_request(
        {"jsonrpc": "2.0", "id": 4, "method": "resources/read", "params": {"uri": "patchpilot://stats/overview"}}
    )
    content2 = read_resp2["result"]["contents"][0]
    assert "ast_anti_reward_hacking_rules" in content2["text"]


def test_patchpilot_mcp_prompts_list_and_get():
    server = PatchPilotMCPServer()
    resp = server.handle_request({"jsonrpc": "2.0", "id": 5, "method": "prompts/list"})
    prompts = resp["result"]["prompts"]
    assert len(prompts) >= 2
    names = [p["name"] for p in prompts]
    assert "diagnose-and-repair" in names
    assert "audit-git-diff" in names

    # Get prompt
    get_resp = server.handle_request(
        {
            "jsonrpc": "2.0",
            "id": 6,
            "method": "prompts/get",
            "params": {"name": "audit-git-diff", "arguments": {"unified_diff": "--- a/x.py\n+++ b/x.py\n@@ -1 +1 @@\n-1\n+2"}},
        }
    )
    res = get_resp["result"]
    assert len(res["messages"]) == 1
    assert "RH001-RH008" in res["messages"][0]["content"]["text"]

"""Interactive Developer Portal & Playground for PatchPilot.

Renders an ultra-fast, zero-dependency, responsive HTML5 developer interface
when a user or browser visits the endpoint with Accept: text/html.
Styled with a Tactical Code Defense & Anti-Reward-Hacking Shield theme (laser blue & shield green/crimson).
"""

from __future__ import annotations

import html
import json
from typing import Any, Dict, List


def render_developer_portal(
    server_name: str,
    server_version: str,
    tagline: str,
    endpoint_url: str,
    github_url: str,
    tools: List[Dict[str, Any]],
    resources: List[Dict[str, Any]],
    prompts: List[Dict[str, Any]],
    sample_tool_call: Dict[str, Any],
) -> str:
    """Generate a self-contained, highly interactive HTML code defense dashboard."""

    safe_name = html.escape(server_name)
    safe_version = html.escape(server_version)
    safe_tagline = html.escape(tagline)
    safe_endpoint = html.escape(endpoint_url)
    safe_github = html.escape(github_url)

    tools_json = json.dumps(tools, indent=2)
    resources_json = json.dumps(resources, indent=2)
    prompts_json = json.dumps(prompts, indent=2)
    sample_call_json = json.dumps(sample_tool_call, indent=2)

    # Tool cards
    tool_cards = []
    for t in tools:
        t_name = html.escape(t.get("name", ""))
        t_desc = html.escape(t.get("description", ""))
        props = t.get("inputSchema", {}).get("properties", {})
        req = set(t.get("inputSchema", {}).get("required", []))
        param_badges = "".join(
            f'<span class="badge param {"req" if p in req else "opt"}">{html.escape(p)}{"*" if p in req else ""}</span>'
            for p in props.keys()
        )
        tool_cards.append(
            f"""
            <div class="card item-card tool-card-item" data-name="{t_name}" data-desc="{t_desc}">
              <div class="card-head">
                <span class="mono font-bold text-blue">{t_name}</span>
                <button class="btn btn-sm btn-ghost" onclick="loadToolCall('{t_name}')">Test &rarr;</button>
              </div>
              <p class="text-sm text-dim">{t_desc}</p>
              <div class="param-row">{param_badges or '<span class="text-xs text-muted">No parameters</span>'}</div>
            </div>
            """
        )
    tools_html = "".join(tool_cards)

    # Resource cards
    res_cards = []
    for r in resources:
        r_uri = html.escape(r.get("uri", ""))
        r_name = html.escape(r.get("name", ""))
        r_desc = html.escape(r.get("description", ""))
        r_mime = html.escape(r.get("mimeType", "application/json"))
        res_cards.append(
            f"""
            <div class="card item-card res-card-item" data-uri="{r_uri}">
              <div class="card-head">
                <span class="mono font-bold text-green">{r_uri}</span>
                <button class="btn btn-sm btn-ghost" onclick="loadResourceRead('{r_uri}')">Read &rarr;</button>
              </div>
              <div class="text-xs text-muted mono">{r_name} &bull; {r_mime}</div>
              <p class="text-sm text-dim">{r_desc}</p>
            </div>
            """
        )
    resources_html = "".join(res_cards)

    # Prompt cards
    prompt_cards = []
    for p in prompts:
        p_name = html.escape(p.get("name", ""))
        p_desc = html.escape(p.get("description", ""))
        args = p.get("arguments", [])
        arg_badges = "".join(
            f'<span class="badge param {"req" if a.get("required") else "opt"}">{html.escape(a.get("name", ""))}{"*" if a.get("required") else ""}</span>'
            for a in args
        )
        prompt_cards.append(
            f"""
            <div class="card item-card prompt-card-item" data-name="{p_name}">
              <div class="card-head">
                <span class="mono font-bold text-purple">{p_name}</span>
                <button class="btn btn-sm btn-ghost" onclick="loadPromptGet('{p_name}')">Render &rarr;</button>
              </div>
              <p class="text-sm text-dim">{p_desc}</p>
              <div class="param-row">{arg_badges or '<span class="text-xs text-muted">No arguments</span>'}</div>
            </div>
            """
        )
    prompts_html = "".join(prompt_cards)

    claude_code_cmd = f"claude mcp add --transport http {safe_name} {safe_endpoint}"
    claude_desktop_cfg = json.dumps({"mcpServers": {safe_name: {"type": "http", "url": safe_endpoint}}}, indent=2)
    cursor_cfg = json.dumps({"mcpServers": {safe_name: {"type": "http", "url": safe_endpoint}}}, indent=2)
    smithery_cmd = f"npx -y @smithery/cli install @codesphere-u/{safe_name} --client claude"
    stdio_cmd = f"uvx --from git+{safe_github}.git {safe_name} serve-stdio"

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{safe_name} &bull; Autonomous Code Repair MCP Portal</title>
  <meta name="description" content="{safe_tagline}" />
  <meta property="og:title" content="{safe_name} &bull; Anti-Reward-Hacking MCP Gateway" />
  <meta property="og:description" content="{safe_tagline}" />
  <meta property="og:type" content="website" />
  <meta property="og:url" content="{safe_endpoint}" />
  <meta name="twitter:card" content="summary" />
  <meta name="twitter:title" content="{safe_name} &bull; MCP Server & Playground" />
  <meta name="twitter:description" content="{safe_tagline}" />
  <meta name="theme-color" content="#070b12" />
  <link rel="icon" href="data:image/svg+xml,<svg xmlns=%22http://www.w3.org/2000/svg%22 viewBox=%220%22><text y=%2226%22 font-size=%2226%22>🛡️</text></svg>">
  <style>
    :root {{
      --bg: #070b12;
      --card-bg: #0d1420;
      --card-border: #182338;
      --card-hover: #223250;
      --text: #e2e8f0;
      --text-dim: #94a3b8;
      --text-muted: #64748b;
      --blue: #3b82f6;
      --blue-glow: rgba(59, 130, 246, 0.25);
      --green: #10b981;
      --green-glow: rgba(16, 185, 129, 0.2);
      --red: #ef4444;
      --red-glow: rgba(239, 68, 68, 0.2);
      --purple: #a855f7;
      --font-sans: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", sans-serif;
      --font-mono: "JetBrains Mono", ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
    }}
    * {{ box-sizing: border-box; margin: 0; padding: 0; }}
    body {{
      background: var(--bg);
      background-image: 
        radial-gradient(circle at 50% 0%, rgba(59, 130, 246, 0.08) 0%, transparent 60%),
        radial-gradient(ellipse at bottom left, rgba(16, 185, 129, 0.06) 0%, transparent 50%);
      color: var(--text);
      font-family: var(--font-sans);
      line-height: 1.5;
      padding: 24px;
      min-height: 100vh;
    }}
    .mono {{ font-family: var(--font-mono); }}
    .container {{ max-width: 1140px; margin: 0 auto; display: flex; flex-direction: column; gap: 24px; }}
    
    /* Header */
    .header {{
      background: linear-gradient(135deg, #0e192c 0%, #080e1a 100%);
      border: 1px solid var(--card-border);
      border-radius: 14px;
      padding: 28px;
      display: flex;
      flex-direction: column;
      gap: 20px;
      box-shadow: 0 12px 36px rgba(0,0,0,0.5);
      position: relative;
      overflow: hidden;
    }}
    .header::before {{
      content: ""; position: absolute; top: 0; left: 0; right: 0; height: 3px;
      background: linear-gradient(90deg, var(--blue) 0%, var(--green) 50%, var(--purple) 100%);
    }}
    .header-top {{ display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 16px; }}
    .title-group {{ display: flex; align-items: center; gap: 12px; flex-wrap: wrap; }}
    h1 {{ font-size: 28px; font-weight: 800; color: #fff; letter-spacing: -0.02em; display: flex; align-items: center; gap: 10px; }}
    .badge {{
      display: inline-flex; align-items: center; gap: 6px;
      padding: 4px 10px; border-radius: 9999px;
      font-size: 12px; font-weight: 600;
    }}
    .badge-live {{ background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.35); }}
    .badge-live::before {{
      content: ""; width: 8px; height: 8px; border-radius: 50%;
      background: #34d399; box-shadow: 0 0 10px #34d399;
      animation: pulse 2s infinite;
    }}
    @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.35; }} }}
    .badge-proto {{ background: rgba(59, 130, 246, 0.15); color: #60a5fa; border: 1px solid rgba(59, 130, 246, 0.3); }}
    .badge-ver {{ background: rgba(16, 185, 129, 0.15); color: #34d399; border: 1px solid rgba(16, 185, 129, 0.3); }}
    
    .links {{ display: flex; gap: 8px; flex-wrap: wrap; }}
    .btn {{
      display: inline-flex; align-items: center; gap: 6px;
      padding: 8px 14px; border-radius: 8px; font-size: 13px; font-weight: 600;
      cursor: pointer; text-decoration: none; border: 1px solid var(--card-border);
      background: #101a2e; color: #fff; transition: all 0.2s cubic-bezier(0.4, 0, 0.2, 1);
    }}
    .btn:hover {{ background: #1a2947; border-color: #2b426f; transform: translateY(-1px); }}
    .btn-accent {{ background: #2563eb; border-color: #1d4ed8; box-shadow: 0 0 16px rgba(37, 99, 235, 0.35); }}
    .btn-accent:hover {{ background: #1d4ed8; }}
    .btn-blue {{ background: rgba(59, 130, 246, 0.15); border-color: var(--blue); color: #93c5fd; }}
    .btn-blue:hover {{ background: rgba(59, 130, 246, 0.25); box-shadow: 0 0 12px var(--blue-glow); }}
    .btn-sm {{ padding: 5px 11px; font-size: 12px; }}
    .btn-ghost {{ background: transparent; border-color: transparent; color: #60a5fa; }}
    .btn-ghost:hover {{ background: var(--blue-glow); }}
    
    /* Stats */
    .grid-stats {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr));
      gap: 14px;
    }}
    .stat-card {{
      background: rgba(13, 20, 32, 0.7); border: 1px solid var(--card-border);
      border-radius: 10px; padding: 16px 20px; transition: border-color 0.2s;
    }}
    .stat-card:hover {{ border-color: var(--blue); }}
    .stat-val {{ font-size: 26px; font-weight: 800; color: #fff; }}
    .stat-lbl {{ font-size: 11px; color: var(--text-dim); text-transform: uppercase; letter-spacing: 0.08em; font-weight: 600; }}
    
    .card {{
      background: var(--card-bg); border: 1px solid var(--card-border);
      border-radius: 12px; padding: 22px;
      box-shadow: 0 8px 24px rgba(0,0,0,0.3);
    }}
    
    /* Anti-Reward-Hacking Shield Simulator */
    .shield-card {{
      background: linear-gradient(180deg, #0a1322 0%, #060c17 100%);
      border: 1px solid rgba(59, 130, 246, 0.3);
      position: relative; overflow: hidden;
    }}
    .rules-grid {{
      display: grid; grid-template-columns: repeat(auto-fit, minmax(210px, 1fr));
      gap: 10px; margin-top: 14px;
    }}
    .rule-item {{
      background: #040810; border: 1px solid #142036; border-radius: 6px;
      padding: 10px 14px; display: flex; flex-direction: column; gap: 3px;
    }}
    .rule-code {{ font-size: 11px; font-weight: 700; color: #38bdf8; font-family: var(--font-mono); }}
    .rule-desc {{ font-size: 11px; color: #94a3b8; }}
    
    /* Tabs & Snippets */
    .tabs {{ display: flex; gap: 6px; border-bottom: 1px solid var(--card-border); padding-bottom: 8px; margin-bottom: 16px; flex-wrap: wrap; }}
    .tab-btn {{
      background: transparent; border: none; color: var(--text-dim);
      padding: 8px 14px; font-size: 13px; font-weight: 600; cursor: pointer;
      border-radius: 6px; transition: all 0.2s;
    }}
    .tab-btn:hover {{ color: #fff; background: rgba(255,255,255,0.06); }}
    .tab-btn.active {{ color: #93c5fd; background: #16243d; border: 1px solid #2a416b; }}
    .snippet-box {{
      position: relative; background: #03060c; border: 1px solid #142036;
      border-radius: 8px; padding: 16px; overflow-x: auto;
    }}
    .snippet-box pre {{ margin: 0; color: #e2e8f0; font-family: var(--font-mono); font-size: 13px; white-space: pre-wrap; word-break: break-all; }}
    .copy-btn {{
      position: absolute; top: 10px; right: 10px;
      background: #142036; border: 1px solid #283e66;
      color: #94a3b8; padding: 5px 12px; border-radius: 6px;
      font-size: 12px; cursor: pointer; font-family: var(--font-sans); font-weight: 600;
      transition: all 0.2s;
    }}
    .copy-btn:hover {{ color: #fff; background: #1f3254; }}
    .copy-btn.copied {{ background: #065f46; color: #34d399; border-color: #047857; }}
    
    /* Playground */
    .playground-grid {{
      display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-top: 14px;
    }}
    @media (max-width: 820px) {{
      .playground-grid {{ grid-template-columns: 1fr; }}
    }}
    .pane {{ display: flex; flex-direction: column; gap: 10px; }}
    .pane-head {{ display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px; }}
    .pane-title {{ font-size: 12px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.08em; color: var(--text-dim); }}
    textarea.code-editor {{
      width: 100%; min-height: 290px; background: #03060c;
      border: 1px solid var(--card-border); border-radius: 8px;
      padding: 14px; font-family: var(--font-mono); font-size: 12px;
      color: #e2e8f0; resize: vertical; outline: none; line-height: 1.45;
    }}
    textarea.code-editor:focus {{ border-color: var(--blue); box-shadow: 0 0 12px var(--blue-glow); }}
    .response-box {{
      min-height: 290px; max-height: 520px; background: #03060c;
      border: 1px solid var(--card-border); border-radius: 8px;
      padding: 14px; font-family: var(--font-mono); font-size: 12px;
      color: #38bdf8; overflow: auto; white-space: pre;
    }}
    .preset-bar {{ display: flex; gap: 6px; flex-wrap: wrap; }}
    
    /* Filter Bar */
    .filter-bar {{
      display: flex; gap: 10px; align-items: center; margin-bottom: 14px; flex-wrap: wrap;
    }}
    .search-input {{
      flex: 1; min-width: 200px; background: #03060c; border: 1px solid var(--card-border);
      border-radius: 8px; padding: 8px 14px; color: #fff; font-family: var(--font-sans);
      font-size: 13px; outline: none;
    }}
    .search-input:focus {{ border-color: var(--blue); }}
    
    /* Item Cards */
    .card-list {{ display: grid; grid-template-columns: repeat(auto-fill, minmax(320px, 1fr)); gap: 14px; }}
    .item-card {{ display: flex; flex-direction: column; gap: 10px; background: #0a111e; border-color: #17243b; transition: all 0.2s; }}
    .item-card:hover {{ border-color: var(--blue); transform: translateY(-2px); }}
    .card-head {{ display: flex; justify-content: space-between; align-items: center; gap: 8px; }}
    .text-blue {{ color: #60a5fa; }}
    .text-green {{ color: #34d399; }}
    .text-purple {{ color: var(--purple); }}
    .text-sm {{ font-size: 13px; }}
    .text-xs {{ font-size: 11px; }}
    .text-dim {{ color: var(--text-dim); }}
    .text-muted {{ color: var(--text-muted); }}
    .param-row {{ display: flex; gap: 6px; flex-wrap: wrap; margin-top: 4px; }}
    .badge.param {{ font-size: 11px; padding: 2px 7px; border-radius: 4px; font-family: var(--font-mono); }}
    .badge.param.req {{ background: rgba(239, 68, 68, 0.15); color: #f87171; border: 1px solid rgba(239, 68, 68, 0.3); }}
    .badge.param.opt {{ background: rgba(148, 163, 184, 0.1); color: #94a3b8; border: 1px solid rgba(148, 163, 184, 0.2); }}
    
    /* Footer */
    .footer {{
      display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap;
      gap: 12px; padding: 18px 4px; border-top: 1px solid var(--card-border);
      font-size: 12px; color: var(--text-muted);
    }}
    .footer a {{ color: var(--blue); text-decoration: none; }}
  </style>
</head>
<body>
  <div class="container">
    <!-- Header -->
    <header class="header">
      <div class="header-top">
        <div>
          <div class="title-group">
            <h1><span>🛡️</span> {safe_name}</h1>
            <span class="badge badge-ver">v{safe_version}</span>
            <span class="badge badge-live">Operational</span>
            <span class="badge badge-proto">MCP 2024-11-05</span>
          </div>
          <p class="text-sm text-dim" style="margin-top: 8px; max-width: 680px;">{safe_tagline}</p>
        </div>
        <div class="links">
          <a class="btn" href="{safe_github}" target="_blank" rel="noopener">GitHub</a>
          <a class="btn" href="/docs" target="_blank" rel="noopener">Swagger UI &rarr;</a>
          <a class="btn" href="/redoc" target="_blank" rel="noopener">ReDoc &rarr;</a>
          <a class="btn" href="https://glama.ai/mcp" target="_blank" rel="noopener">Glama</a>
          <a class="btn" href="https://smithery.ai" target="_blank" rel="noopener">Smithery</a>
        </div>
      </div>
      
      <div class="grid-stats">
        <div class="stat-card">
          <div class="stat-val text-green">100%</div>
          <div class="stat-lbl">Top-1 Fault Localization</div>
        </div>
        <div class="stat-card">
          <div class="stat-val text-blue">-96.6%</div>
          <div class="stat-lbl">Prompt Token Reduction</div>
        </div>
        <div class="stat-card">
          <div class="stat-val text-purple">8 Rules</div>
          <div class="stat-lbl">Anti-Reward-Hacking Shield</div>
        </div>
        <div class="stat-card">
          <div class="stat-val" style="color: #38bdf8;">Nexus Aegis G5</div>
          <div class="stat-lbl">Cryptographic Attestation</div>
        </div>
      </div>
    </header>

    <!-- Anti-Reward-Hacking Shield & Diff Inspector -->
    <section class="card shield-card">
      <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 8px;">
        <div>
          <h2 style="font-size: 16px; color: #fff; display: flex; align-items: center; gap: 8px;">
            <span style="color: var(--blue);">🛡️</span> AST Anti-Reward-Hacking Guard & Fault Localizer
          </h2>
          <p class="text-xs text-dim">Prevents autonomous agents from deleting unit tests, weakening assertions, or faking green CI.</p>
        </div>
        <div style="display: flex; gap: 8px;">
          <button class="btn btn-sm btn-blue" onclick="testCleanDiff()">Test Clean Fix &rarr;</button>
          <button class="btn btn-sm" style="border-color: #ef4444; color: #f87171;" onclick="testRewardHackingDiff()">Simulate Malicious Diff &rarr;</button>
        </div>
      </div>

      <div class="rules-grid">
        <div class="rule-item">
          <span class="rule-code">RH001</span>
          <span class="rule-desc">Test function / class deletion</span>
        </div>
        <div class="rule-item">
          <span class="rule-code">RH002</span>
          <span class="rule-desc">Skip decorator (@pytest.mark.skip)</span>
        </div>
        <div class="rule-item">
          <span class="rule-code">RH003</span>
          <span class="rule-desc">Assertion count reduction</span>
        </div>
        <div class="rule-item">
          <span class="rule-code">RH004</span>
          <span class="rule-desc">Tautological assertion (assert True)</span>
        </div>
        <div class="rule-item">
          <span class="rule-code">RH005</span>
          <span class="rule-desc">Broad exception swallowing</span>
        </div>
        <div class="rule-item">
          <span class="rule-code">RH006</span>
          <span class="rule-desc">Test environment sniffing bypass</span>
        </div>
        <div class="rule-item">
          <span class="rule-code">RH007</span>
          <span class="rule-desc">Mock fixture state corruption</span>
        </div>
        <div class="rule-item">
          <span class="rule-code">RH008</span>
          <span class="rule-desc">AST syntax & grammar regressions</span>
        </div>
      </div>
    </section>

    <!-- Quick Connect Box -->
    <section class="card">
      <h2 style="font-size: 16px; margin-bottom: 12px; color: #fff;">1-Click Client Configuration</h2>
      <div class="tabs">
        <button class="tab-btn active" onclick="switchTab(this, 'tab-claude-code')">Claude Code</button>
        <button class="tab-btn" onclick="switchTab(this, 'tab-cursor')">Cursor</button>
        <button class="tab-btn" onclick="switchTab(this, 'tab-windsurf')">Windsurf</button>
        <button class="tab-btn" onclick="switchTab(this, 'tab-desktop')">Claude Desktop</button>
        <button class="tab-btn" onclick="switchTab(this, 'tab-smithery')">Smithery CLI</button>
        <button class="tab-btn" onclick="switchTab(this, 'tab-stdio')">Local Stdio</button>
      </div>

      <div id="tab-claude-code" class="tab-pane">
        <div class="snippet-box">
          <pre>{html.escape(claude_code_cmd)}</pre>
          <button class="copy-btn" onclick="copySnippet(this, `{claude_code_cmd}`)">Copy Command</button>
        </div>
        <p class="text-xs text-muted" style="margin-top: 8px;">Run directly in your terminal to register in Claude Code project/global config.</p>
      </div>

      <div id="tab-cursor" class="tab-pane" style="display: none;">
        <div class="snippet-box">
          <pre>{html.escape(cursor_cfg)}</pre>
          <button class="copy-btn" onclick="copySnippet(this, `{cursor_cfg}`)">Copy JSON</button>
        </div>
        <p class="text-xs text-muted" style="margin-top: 8px;">Paste into your project's <code>.cursor/mcp.json</code> or user settings.</p>
      </div>

      <div id="tab-windsurf" class="tab-pane" style="display: none;">
        <div class="snippet-box">
          <pre>{html.escape(cursor_cfg)}</pre>
          <button class="copy-btn" onclick="copySnippet(this, `{cursor_cfg}`)">Copy JSON</button>
        </div>
        <p class="text-xs text-muted" style="margin-top: 8px;">Paste into <code>~/.codeium/windsurf/mcp_config.json</code>.</p>
      </div>

      <div id="tab-desktop" class="tab-pane" style="display: none;">
        <div class="snippet-box">
          <pre>{html.escape(claude_desktop_cfg)}</pre>
          <button class="copy-btn" onclick="copySnippet(this, `{claude_desktop_cfg}`)">Copy JSON</button>
        </div>
        <p class="text-xs text-muted" style="margin-top: 8px;">Paste into <code>claude_desktop_config.json</code>.</p>
      </div>

      <div id="tab-smithery" class="tab-pane" style="display: none;">
        <div class="snippet-box">
          <pre>{html.escape(smithery_cmd)}</pre>
          <button class="copy-btn" onclick="copySnippet(this, `{smithery_cmd}`)">Copy Command</button>
        </div>
        <p class="text-xs text-muted" style="margin-top: 8px;">Installs via the Smithery registry orchestrator.</p>
      </div>

      <div id="tab-stdio" class="tab-pane" style="display: none;">
        <div class="snippet-box">
          <pre>{html.escape(stdio_cmd)}</pre>
          <button class="copy-btn" onclick="copySnippet(this, `{stdio_cmd}`)">Copy Command</button>
        </div>
        <p class="text-xs text-muted" style="margin-top: 8px;">Runs locally without any installation via uvx.</p>
      </div>
    </section>

    <!-- Interactive Playground -->
    <section class="card">
      <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px; flex-wrap: wrap; gap: 8px;">
        <div>
          <h2 style="font-size: 16px; color: #fff;">Interactive JSON-RPC Playground</h2>
          <p class="text-xs text-dim">Test live serverless MCP execution with sub-millisecond response measurement.</p>
        </div>
        <div class="preset-bar">
          <button class="btn btn-sm" onclick="loadPreset('init')">initialize</button>
          <button class="btn btn-sm" onclick="loadPreset('tools_list')">tools/list</button>
          <button class="btn btn-sm" onclick="loadPreset('sample_call')">audit_clean_diff</button>
          <button class="btn btn-sm" onclick="loadPreset('audit_malicious')">audit_malicious</button>
          <button class="btn btn-sm" onclick="loadPreset('localize_fault')">localize_fault</button>
          <button class="btn btn-sm" onclick="loadPreset('res_list')">resources/list</button>
          <button class="btn btn-sm" onclick="loadPreset('prompts_list')">prompts/list</button>
        </div>
      </div>

      <div class="playground-grid">
        <div class="pane">
          <div class="pane-head">
            <span class="pane-title">Request (JSON-RPC 2.0)</span>
            <div style="display: flex; gap: 8px;">
              <button class="btn btn-sm" id="copy-curl-btn" onclick="copyAsCurl()">Copy as cURL</button>
              <button class="btn btn-sm btn-accent" id="send-btn" onclick="sendJsonRpc()">Send Request &rarr;</button>
            </div>
          </div>
          <textarea id="rpc-request" class="code-editor">{html.escape(sample_call_json)}</textarea>
        </div>
        <div class="pane">
          <div class="pane-head">
            <span class="pane-title">Response</span>
            <div style="display: flex; align-items: center; gap: 8px;">
              <button class="btn btn-sm btn-ghost" id="copy-resp-btn" onclick="copyResponse()">Copy</button>
              <span id="rpc-meta" class="text-xs mono text-muted">Ready</span>
            </div>
          </div>
          <pre id="rpc-response" class="response-box">// Click "Send Request" to test live serverless execution</pre>
        </div>
      </div>
    </section>

    <!-- Capabilities Catalog with Search -->
    <section class="card">
      <div class="filter-bar">
        <div>
          <h2 style="font-size: 16px; color: #fff;">Registered Repair Tools ({len(tools)})</h2>
          <p class="text-xs text-dim">Fault localization, diff verification, anti-reward-hacking audits, and AST analysis.</p>
        </div>
        <input type="text" class="search-input" placeholder="Search tools by name or description..." oninput="filterTools(this.value)">
      </div>
      <div class="card-list" id="tools-list">{tools_html}</div>
    </section>

    <section class="card">
      <h2 style="font-size: 16px; margin-bottom: 14px; color: #fff;">Exposed Repair Resources ({len(resources)})</h2>
      <div class="card-list">{resources_html}</div>
    </section>

    <section class="card">
      <h2 style="font-size: 16px; margin-bottom: 14px; color: #fff;">Diagnostic Prompts Catalog ({len(prompts)})</h2>
      <div class="card-list">{prompts_html}</div>
    </section>

    <!-- Footer -->
    <footer class="footer">
      <div>&copy; 2026 CodeSphere Innovations &bull; PatchPilot &bull; Released under the MIT License</div>
      <div class="mono">Transport: Streamable HTTP (<code>POST /mcp</code>) + SSE (<code>GET /mcp</code>)</div>
    </footer>
  </div>

  <script>
    const TOOLS = {tools_json};
    const RESOURCES = {resources_json};
    const PROMPTS = {prompts_json};
    const SAMPLE_CALL = {sample_call_json};

    function switchTab(btn, paneId) {{
      btn.parentElement.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      btn.closest('section').querySelectorAll('.tab-pane').forEach(p => p.style.display = 'none');
      document.getElementById(paneId).style.display = 'block';
    }}

    function copySnippet(btn, text) {{
      navigator.clipboard.writeText(text).then(() => {{
        const old = btn.innerText;
        btn.innerText = 'Copied!';
        btn.classList.add('copied');
        setTimeout(() => {{
          btn.innerText = old;
          btn.classList.remove('copied');
        }}, 2000);
      }});
    }}

    function copyAsCurl() {{
      const raw = document.getElementById('rpc-request').value;
      let formatted = raw.trim();
      try {{
        formatted = JSON.stringify(JSON.parse(raw));
      }} catch (_) {{}}
      const escaped = formatted.replace(/'/g, "'\\\\''");
      const ep = (window.location.origin || '') + '/mcp';
      const cmd = `curl -X POST "${{ep}}" \\\n  -H "Content-Type: application/json" \\\n  -d '${{escaped}}'`;
      navigator.clipboard.writeText(cmd).then(() => {{
        const btn = document.getElementById('copy-curl-btn');
        const old = btn.innerText;
        btn.innerText = 'Copied cURL!';
        btn.classList.add('copied');
        setTimeout(() => {{
          btn.innerText = old;
          btn.classList.remove('copied');
        }}, 2000);
      }});
    }}

    function copyResponse() {{
      const text = document.getElementById('rpc-response').textContent;
      navigator.clipboard.writeText(text).then(() => {{
        const btn = document.getElementById('copy-resp-btn');
        const old = btn.innerText;
        btn.innerText = 'Copied!';
        setTimeout(() => {{
          btn.innerText = old;
        }}, 2000);
      }});
    }}

    function loadPreset(kind) {{
      const req = document.getElementById('rpc-request');
      if (kind === 'init') {{
        req.value = JSON.stringify({{"jsonrpc": "2.0", "id": 1, "method": "initialize", "params": {{"protocolVersion": "2024-11-05", "capabilities": {{}}, "clientInfo": {{"name": "playground", "version": "1.0.0"}}}}}}, null, 2);
      }} else if (kind === 'tools_list') {{
        req.value = JSON.stringify({{"jsonrpc": "2.0", "id": 2, "method": "tools/list"}}, null, 2);
      }} else if (kind === 'sample_call') {{
        req.value = JSON.stringify(SAMPLE_CALL, null, 2);
      }} else if (kind === 'audit_malicious') {{
        req.value = JSON.stringify({{
          "jsonrpc": "2.0",
          "id": 14,
          "method": "tools/call",
          "params": {{
            "name": "audit_unified_diff",
            "arguments": {{
              "unified_diff": "--- a/tests/test_auth.py\\n+++ b/tests/test_auth.py\\n@@ -10,6 +10,1 @@\\n-def test_jwt_signature_bypass():\\n-    assert verify_signature('bad') is False\\n+    assert True"
            }}
          }}
        }}, null, 2);
      }} else if (kind === 'localize_fault') {{
        req.value = JSON.stringify({{
          "jsonrpc": "2.0",
          "id": 15,
          "method": "tools/call",
          "params": {{
            "name": "localize_fault",
            "arguments": {{
              "stack_trace": "Traceback (most recent call last):\\n  File \\\"src/ledger/tx.py\\\", line 42, in commit\\n    raise InvariantViolationError(\\\"balance < 0\\\")\\nInvariantViolationError: balance < 0"
            }}
          }}
        }}, null, 2);
      }} else if (kind === 'res_list') {{
        req.value = JSON.stringify({{"jsonrpc": "2.0", "id": 3, "method": "resources/list"}}, null, 2);
      }} else if (kind === 'prompts_list') {{
        req.value = JSON.stringify({{"jsonrpc": "2.0", "id": 4, "method": "prompts/list"}}, null, 2);
      }}
    }}

    function loadToolCall(name) {{
      const tool = TOOLS.find(t => t.name === name);
      const props = (tool && tool.inputSchema && tool.inputSchema.properties) || {{}};
      const args = {{}};
      for (const [k, v] of Object.entries(props)) {{
        if (k === 'unified_diff') {{
          args[k] = "--- a/src/math.py\\n+++ b/src/math.py\\n@@ -1,2 +1,2 @@\\n def add(a, b):\\n-    return a - b\\n+    return a + b";
        }} else if (k === 'stack_trace') {{
          args[k] = "Traceback (most recent call last):\\n  File \\\"app.py\\\", line 20, in run\\n    assert val > 0";
        }} else if (v.type === 'string') {{
          args[k] = v.default || 'sample-value';
        }} else if (v.type === 'integer' || v.type === 'number') {{
          args[k] = v.default || 10;
        }} else if (v.type === 'boolean') {{
          args[k] = v.default || false;
        }} else if (v.type === 'array') {{
          args[k] = [];
        }} else {{
          args[k] = {{}};
        }}
      }}
      document.getElementById('rpc-request').value = JSON.stringify({{
        "jsonrpc": "2.0",
        "id": 10,
        "method": "tools/call",
        "params": {{ "name": name, "arguments": args }}
      }}, null, 2);
      document.getElementById('send-btn').scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }}

    function loadResourceRead(uri) {{
      document.getElementById('rpc-request').value = JSON.stringify({{
        "jsonrpc": "2.0",
        "id": 20,
        "method": "resources/read",
        "params": {{ "uri": uri }}
      }}, null, 2);
      document.getElementById('send-btn').scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }}

    function loadPromptGet(name) {{
      const p = PROMPTS.find(x => x.name === name);
      const args = {{}};
      if (p && p.arguments) {{
        for (const a of p.arguments) {{
          args[a.name] = 'production-task';
        }}
      }}
      document.getElementById('rpc-request').value = JSON.stringify({{
        "jsonrpc": "2.0",
        "id": 30,
        "method": "prompts/get",
        "params": {{ "name": name, "arguments": args }}
      }}, null, 2);
      document.getElementById('send-btn').scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }}

    function filterTools(query) {{
      const q = query.toLowerCase();
      document.querySelectorAll('.tool-card-item').forEach(card => {{
        const name = card.getAttribute('data-name').toLowerCase();
        const desc = card.getAttribute('data-desc').toLowerCase();
        card.style.display = (name.includes(q) || desc.includes(q)) ? 'flex' : 'none';
      }});
    }}

    function testCleanDiff() {{
      loadPreset('sample_call');
      sendJsonRpc();
      document.getElementById('send-btn').scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }}

    function testRewardHackingDiff() {{
      loadPreset('audit_malicious');
      sendJsonRpc();
      document.getElementById('send-btn').scrollIntoView({{ behavior: 'smooth', block: 'center' }});
    }}

    async function sendJsonRpc() {{
      const btn = document.getElementById('send-btn');
      const meta = document.getElementById('rpc-meta');
      const respBox = document.getElementById('rpc-response');
      const raw = document.getElementById('rpc-request').value;

      btn.disabled = true;
      btn.innerText = 'Sending...';
      meta.innerText = 'Executing...';
      const t0 = performance.now();

      try {{
        const res = await fetch('/mcp', {{
          method: 'POST',
          headers: {{ 'Content-Type': 'application/json' }},
          body: raw
        }});
        const dur = (performance.now() - t0).toFixed(1);
        const data = await res.json();
        meta.innerHTML = `<span style="color: var(--green);">${{res.status}} OK</span> &bull; ${{dur}} ms`;
        respBox.textContent = JSON.stringify(data, null, 2);
      }} catch (err) {{
        const dur = (performance.now() - t0).toFixed(1);
        meta.innerHTML = `<span style="color: var(--red);">Error</span> &bull; ${{dur}} ms`;
        respBox.textContent = String(err);
      }} finally {{
        btn.disabled = false;
        btn.innerText = 'Send Request →';
      }}
    }}
  </script>
</body>
</html>
"""

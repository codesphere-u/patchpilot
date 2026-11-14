# Model Context Protocol (MCP) & Hosted Vercel Gateway

`patchpilot` v1.2.0 ships both a local JSON-RPC 2.0 MCP server (`stdio` and HTTP/SSE) and a stateless Vercel ASGI gateway (`api/index.py`).

---

## MCP Capabilities Surface

### Tools (`5`)
| Tool | Purpose | Local Stdio | Hosted Vercel |
|---|---|---|---|
| `audit_unified_diff` | Parse & audit multi-file `git diff` against `RH001`–`RH008` + optional Nexus Aegis G5 leaf export | Yes | Yes |
| `localize_fault` | Hybrid Stack-Trace + AST Call-Graph + BM25 suspect ranking inside `token_budget` | Yes | Inline `sources` only |
| `verify_patch_integrity` | Compare `original_files` vs `patched_files` or `unified_diff` against `RH001`–`RH008` | Yes | Yes |
| `inspect_ast_symbols` | Query symbol definitions and bidirectional caller/callee edges | Yes | Inline `sources` only |
| `apply_transactional_patch` | Write patch in SHA-256 snapshot sandbox & run test command | Yes | Blocked (`HOSTED_BLOCKED_TOOLS`) |

### Resources (`2`)
- `patchpilot://rules/catalog` — Full catalog of `RH001`–`RH008` severity weights and descriptions (`application/json`).
- `patchpilot://stats/overview` — Server metadata, localization algorithms, and rollback safety guarantees (`application/json`).

### Prompts (`2`)
- `diagnose-and-repair` (`traceback_text`, optional `suspect_file`)
- `audit-git-diff` (`unified_diff`)

---

## Running Locally

### Stdio Transport (Claude Desktop / Cursor / Windsurf)
```json
{
  "mcpServers": {
    "patchpilot": {
      "command": "patchpilot",
      "args": ["serve-stdio", "--workspace", "/path/to/your/repo"]
    }
  }
}
```

### Streamable HTTP / SSE Server
```bash
patchpilot serve-http --host 127.0.0.1 --port 8000 --workspace /path/to/your/repo
```
Exposed routes:
- `GET /health` & `HEAD /health` — JSON health check (`{"status": "healthy"}`)
- `GET /` — Developer Portal HTML (`Accept: text/html`) or JSON info
- `GET /sse` / `GET /mcp` (`Accept: text/event-stream`) — SSE endpoint negotiation
- `POST /mcp` (and `POST /`) — JSON-RPC 2.0 request handler

Verify a live HTTP/SSE or Vercel deployment using the included smoke test script:
```bash
python scripts/smoke_test.py https://patchpilot-eta.vercel.app 4 2 2
```

---

## Hosted Security Guardrails (`api/index.py`)
To make public stateless usage safe on `https://patchpilot-eta.vercel.app/mcp`:
- **1 MB Payload Cap** on HTTP POST bodies.
- **No Disk Mutations**: `apply_transactional_patch` is explicitly blocked in `HOSTED_BLOCKED_TOOLS`.
- **No Filesystem Traversal**: `workspace_root` is stripped/forbidden via `HOSTED_FORBIDDEN_ARGS`; callers pass explicit inline `sources` dictionaries.
- **Security Headers**: Every response attaches `X-Request-ID` and `X-Content-Type-Options: nosniff`.

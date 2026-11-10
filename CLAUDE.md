# CLAUDE.md — PatchPilot Engineering Guide

## Project Overview
`patchpilot` is a zero-dependency, pure Python 3.10+ **Autonomous Code Repair Engine, AST Call-Graph Fault Localizer, Anti-Reward-Hacking Patch Verifier (`RH001`–`RH008`), and Transactional Patch Sandbox**. It eliminates context-window flooding by pinpointing faulty code slices from test tracebacks and prevents AI coding agents from cheating tests (e.g. deleting assertions, skipping tests, weakening expectations).

* **Package Name (PyPI)**: `patchpilot` (CLI entry point: `patchpilot`, module: `patchpilot`)
* **MCP Specification**: Tripartite support for **Tools**, **Resources**, and **Prompts** (Protocol version `2024-11-05`).
* **Hosted Production**: `https://patchpilot-eta.vercel.app/mcp` (Vercel Serverless Streamable HTTP + SSE).
* **Interactive Portal**: `https://patchpilot-eta.vercel.app/` (Developer Playground).

---

## Build, Test & Lint Commands

```bash
# Run the complete test suite
uv run pytest

# Run tests with verbose output
uv run pytest -v

# Run the built-in reproducible benchmark suite
uv run python -m patchpilot.cli benchmark

# Run the fault localization and repair demo
uv run python -m patchpilot.cli demo

# Audit a candidate git diff for reward-hacking rules (RH001-RH008)
uv run python -m patchpilot.cli audit-diff --diff-file path/to/patch.diff

# Build sdist and wheel distributions
uv build

# Run local stdio MCP server
uv run python -m patchpilot.cli serve-stdio
```

---

## Architecture & Code Structure

```text
src/patchpilot/
├── __init__.py         # Package exports
├── localizer.py        # FaultLocalizer: Stack-trace + AST call-graph + BM25 spectrum fault localization
├── guard.py            # PatchGuard: 8 AST anti-reward-hacking rules (RH001-RH008)
├── diff_parser.py      # UnifiedDiffParser: line-level patch hunk extraction and AST symbol mapping
├── sandbox.py          # TransactionalPatchSandbox: snapshot-backed atomic rollback sandbox
├── aegis_bridge.py     # Nexus Aegis G4 code repair receipt exporter
├── server.py           # PatchPilotMCPServer: Model Context Protocol JSON-RPC 2.0 engine
└── cli.py              # CLI commands (demo, benchmark, audit-diff, export-aegis, serve-stdio)

api/
├── index.py            # Vercel Serverless FastAPI gateway (rate-limited, sandboxed)
└── portal.py           # Zero-dependency interactive Developer Portal & Playground
```

---

## Model Context Protocol (MCP) Primitives

### 1. Tools (`tools/list`, `tools/call`)
* `audit_unified_diff`: Audit a unified git diff against 8 AST anti-reward-hacking rules (`RH001`–`RH008`). Available on public hosted Vercel endpoint.
* `localize_fault`: Localize the exact suspect functions from a pytest traceback and extract line-numbered AST slices.
* `verify_patch_integrity`: Compute cryptographic SHA-256 diff digests and assert that no test files were tampered with.
* `inspect_ast_symbols`: Extract top-level classes, functions, and docstrings from Python source files without file reads.
* `apply_transactional_patch`: Apply a candidate patch inside an isolated sandbox with automatic rollback (stdio).

### 2. Resources (`resources/list`, `resources/read`)
* `patchpilot://rules/catalog`: The 8 AST anti-reward-hacking rules (`RH001`–`RH008`) with rule severities and patterns.
* `patchpilot://stats/overview`: Overview of supported Python AST node visitors and fault localization specs.

### 3. Prompts (`prompts/list`, `prompts/get`)
* `diagnose-and-repair`: Step-by-step guided prompt to localize root cause from a traceback and inspect suspect AST slices.
* `audit-git-diff`: Structured code review prompt to audit unified diffs for reward-hacking anti-patterns.

---

## Claude Code Quick-Connect

```bash
# Add to Claude Code project scope:
claude mcp add --transport http patchpilot https://patchpilot-eta.vercel.app/mcp

# Or user scope (globally across all projects):
claude mcp add --scope user --transport http patchpilot https://patchpilot-eta.vercel.app/mcp
```

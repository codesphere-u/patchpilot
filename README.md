# `patchpilot` — Autonomous Code Repair Engine

[![CI](https://github.com/codesphere-u/patchpilot/actions/workflows/ci.yml/badge.svg)](https://github.com/codesphere-u/patchpilot/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10%20%7C%203.11%20%7C%203.12-blue.svg)](https://www.python.org/)
[![MCP Compatible](https://img.shields.io/badge/MCP-JSON--RPC%202.0-00b4d8.svg)](https://modelcontextprotocol.io/)
[![Zero Dependencies](https://img.shields.io/badge/dependencies-zero%20runtime-success.svg)](#installation)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

**Stack-Trace & AST Call-Graph Fault Localizer, Deterministic Anti-Reward-Hacking Patch Verifier (`RH001`–`RH008`), Transactional Rollback Sandbox, and Model Context Protocol (MCP) Server for Autonomous Coding Agents.**

---

## Why `patchpilot` Exists: The Two Failure Modes of Coding Agents

Modern autonomous software engineering loops (OpenHands, SWE-agent, Claude Code, Devin-style test-repair loops) fail in production for two recurring reasons:

1. **Context-Window Flooding During Fault Localization:** Dumping dozens of repository files into an LLM prompt when a pytest run fails wastes 90%+ of context tokens and confuses the model. Agents need deterministic **Stack-Trace + AST Call-Graph + BM25 Spectrum Fault Localization** to isolate the exact suspect functions and extract minimal, line-numbered AST slices within a strict token budget.
2. **Reward Hacking / Test Tampering by Coding Agents:** When an LLM agent is rewarded for making `pytest` exit with code `0`, it frequently "cheats" instead of fixing the root cause—deleting `test_*` functions, injecting `@pytest.mark.skip` or `pytest.xfail()`, weakening `assert x == y` into `assert True`, altering expected test constants, or wrapping buggy code in `except Exception: pass`.

`patchpilot` solves both problems in a **zero-runtime-dependency Python 3.10+ package** with a CLI, Python SDK, and **JSON-RPC 2.0 MCP Server**.

---

## Architecture Overview

```text
  Failing Pytest / Traceback Log                    Candidate Agent Patch (Diff / Files)
                │                                                    │
                ▼                                                    ▼
┌───────────────────────────────────────┐    ┌──────────────────────────────────────────────┐
│  1. FaultLocalizer & ASTSymbolIndex   │    │  2. PatchIntegrityGuard (AST Verifier)       │
│  ───────────────────────────────────  │    │  ──────────────────────────────────────────  │
│  • Parses Python & pytest tracebacks  │    │  • RH001: Test deletion / @skip / xfail      │
│  • Builds AST symbol table & 2-hop    │    │  • RH002: Assertion removal / tautologies    │
│    bidirectional caller/callee graph  │    │  • RH003: Bare except / Exception swallowing │
│  • Ranks suspects via weighted formula│    │  • RH004: Python AST syntax validation       │
│    (0.55 Stack + 0.25 Graph + 0.20 BM25)   │  • RH005: Dangerous primitives (eval/shell)  │
│  • Emits token-budgeted code slices   │    │  • RH006: Leftover breakpoint() / pdb        │
└──────────────────┬────────────────────┘    │  • RH007: Blast radius limits (files/lines)  │
                   │                         │  • RH008: Protected CI/config file lock      │
                   │                         └──────────────────────┬───────────────────────┘
                   ▼                                                │
         Minimal Context Prompt                                     ▼
          (96.6% token savings)              ┌──────────────────────────────────────────────┐
                                             │  3. TransactionalPatchWorkspace              │
                                             │  ──────────────────────────────────────────  │
                                             │  • Pre-patch SHA-256 byte snapshots          │
                                             │  • Runs test runner / verification callback  │
                                             │  • Automatic byte-exact rollback on failure  │
                                             │  • Emits tamper-evident SHA-256 RepairReceipt│
                                             └──────────────────────────────────────────────┘
```

---

## Anti-Reward-Hacking Rules (`RH001`–`RH008`)

Every candidate patch is evaluated by `PatchIntegrityGuard` via pre-patch vs. post-patch Python `ast` comparison before any test runner is executed:

| Rule ID | Rule Name | Severity | What It Deterministically Blocks |
| :--- | :--- | :---: | :--- |
| **`RH001`** | **Test Deletion or Skip Injection** | Critical | Deleting `test_*` functions/files, injecting `@pytest.mark.skip`, `@pytest.mark.xfail`, `@unittest.skip`, or calling `pytest.skip()` / `self.skipTest()`. |
| **`RH002`** | **Assertion Weakening or Tautology** | Critical | Reducing the number of `assert` / `self.assert*` statements in a test, replacing assertions with tautologies (`assert True`, `assert 1 == 1`), or mutating expected test literals. |
| **`RH003`** | **Broad Exception Swallowing** | High | Introducing bare `except:` or `except (Exception, BaseException):` blocks whose body merely executes `pass`, `...`, `continue`, or returns a literal constant (`return None`). |
| **`RH004`** | **Syntax / AST Parse Failure** | Critical | Producing invalid Python syntax in any modified `.py` file. |
| **`RH005`** | **Forbidden Dangerous Primitives** | Critical | Injecting `eval()`, `exec()`, `__import__()`, `os.system()`, `os.popen()`, or `subprocess.*(..., shell=True)`. |
| **`RH006`** | **Debug Breakpoint Leftovers** | Medium | Leaving `breakpoint()`, `pdb.set_trace()`, or `ipdb.set_trace()` inside patched code. |
| **`RH007`** | **Excessive Blast Radius** | Medium | Touching more than `max_files_touched` (default `5`) or `max_lines_changed` (default `250`). |
| **`RH008`** | **Protected Path Modification** | High | Tampering with `.github/workflows/*`, `pyproject.toml`, `conftest.py`, lockfiles, or `.env` files. |

---

## Reproducible Benchmark Results

Run `patchpilot benchmark` to execute the built-in benchmark suite across 50 indexed modules (100 AST symbols), 25 fault localization scenarios, and 40 patches (20 adversarial reward-hacking patches across `RH001`–`RH008` + 20 legitimate bug fixes):

| Subsystem | Benchmark Workload | Primary Accuracy / Recall | Secondary Metric | p50 Latency | p95 Latency |
| :--- | :--- | :--- | :--- | :---: | :---: |
| **AST Symbol & Call-Graph Indexer** | 50 files / 100 symbols | 100.0% AST parse coverage | Bidirectional call edges | 3.79 ms | 3.79 ms |
| **Hybrid Fault Localizer (`FaultLocalizer`)** | 25 stack & call-graph fault scenarios | **100.0% Top-1** / **100.0% Top-3** | **96.6%** prompt token reduction | 0.373 ms | 0.499 ms |
| **Anti-Reward-Hacking Guard (`RH001`–`RH008`)** | 20 adversarial + 20 legitimate patches | **100.0% Recall** / **100.0% Precision** | **0.0%** False Positive Rate | 0.098 ms | 0.331 ms |

---

## Installation

```bash
git clone https://github.com/codesphere-u/patchpilot.git
cd patchpilot
pip install -e ".[dev]"
```

---

## Quickstart: CLI

### 1. Run the End-to-End Autonomous Repair Demo

```bash
patchpilot demo
```

This creates a synthetic multi-file billing repository with a discount calculation bug, localizes the fault from a pytest failure log to the exact offending functions (`billing/invoice.py::calculate_tiered_invoice` and `billing/pricing.py::apply_volume_discount`) using only `303` tokens, catches and rolls back an adversarial reward-hacking patch (`RH001`, `RH002`, `RH003`), and commits a genuine minimal fix with a verified SHA-256 `RepairReceipt`.

### 2. Run the Benchmark Suite

```bash
patchpilot benchmark
patchpilot benchmark --json
```

---

## Quickstart: Python SDK

```python
from pathlib import Path
from patchpilot import FaultLocalizer, PatchIntegrityGuard, TransactionalPatchWorkspace

workspace = Path("./my_project")

# 1. Localize a failing pytest traceback within a 600-token budget
localizer = FaultLocalizer.from_directory(workspace)
loc = localizer.localize(pytest_stderr_output, top_k=3, token_budget=600)
print(loc.format_context_prompt())

# 2. Apply a candidate patch transactionally (with RH001-RH008 guard + automatic rollback)
sandbox = TransactionalPatchWorkspace(workspace, guard=PatchIntegrityGuard())
receipt = sandbox.apply_patch_transaction(
    patched_files={"billing/pricing.py": fixed_source_code},
    test_command=["pytest", "-q"],
    suspects_considered=[s.symbol.symbol_id for s in loc.suspects],
)

if receipt.status == "committed":
    print(f"Committed! Receipt SHA-256: {receipt.receipt_sha256}")
else:
    print(f"Rolled back at stage={receipt.stage_failed}: {receipt.guard_verdict.violations}")
```

---

## Model Context Protocol (MCP) Server Integration

`patchpilot` includes a full JSON-RPC 2.0 MCP server (`patchpilot serve-stdio`) exposing four deterministic tools to Claude Code, Cursor, OpenHands, or custom MCP clients:

- `localize_fault`: Rank suspect functions from a traceback and return token-budgeted AST slices.
- `verify_patch_integrity`: Evaluate a candidate patch or unified diff against `RH001`–`RH008`.
- `apply_transactional_patch`: Apply a patch inside an atomic snapshot transaction with automatic SHA-256 rollback on guard or test failure.
- `inspect_ast_symbols`: Query the workspace AST symbol table and caller/callee graph by name or `(file_path, line_number)`.

### MCP Client Configuration (`claude_desktop_config.json` / `.cursor/mcp.json`)

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

---

## Architecture Decision Records (ADRs)

- [ADR-001: Deterministic AST Verification Against Coding Agent Reward Hacking (`RH001`–`RH008`)](docs/ADR-001-ast-anti-reward-hacking.md)
- [ADR-002: Hybrid Stack-Trace + AST Call-Graph + BM25 Spectrum Fault Localization](docs/ADR-002-hybrid-fault-localization.md)
- [ADR-003: Snapshot-Backed Transactional Patch Sandbox & Cryptographic Repair Receipts](docs/ADR-003-transactional-sandbox-receipts.md)

---

## Hosted endpoint (Vercel)

A free, public, stateless deployment of PatchPilot runs over **MCP Streamable HTTP**:

| | |
|---|---|
| MCP endpoint | `https://patchpilot-eta.vercel.app/mcp` (JSON-RPC 2.0 over `POST`) |
| Health probe | `https://patchpilot-eta.vercel.app/health` |

```bash
curl -s -X POST https://patchpilot-eta.vercel.app/mcp -H 'Content-Type: application/json' \
  -d '{"jsonrpc":"2.0","id":1,"method":"tools/list"}'
```

Client config (any Streamable-HTTP-capable MCP client):

```json
{ "mcpServers": { "patchpilot": { "url": "https://patchpilot-eta.vercel.app/mcp" } } }
```

**Hosted limitations:** `apply_transactional_patch` (writes files, runs commands) is **disabled on the hosted endpoint**, and `localize_fault` / `inspect_ast_symbols` accept inline `sources` only (no `workspace_root`). Use the local stdio install for full functionality.

The hosted gateway is [`api/index.py`](api/index.py); it enforces a 1 MB body limit, strict JSON-RPC envelopes and the tool restrictions above. Deploy your own copy with `npx vercel deploy --prod` (entrypoint is configured in `pyproject.toml` under `[tool.vercel]`).

## License

MIT License — Copyright (c) 2026 [Akandwanaho Ivan Alvin (`@codesphere-u`)](https://github.com/codesphere-u).

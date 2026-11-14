# Getting Started with PatchPilot

`patchpilot` repairs failing Python test suites and audits candidate diffs cleanly using three deterministic subsystems:
1. **`FaultLocalizer`** — parses Python tracebacks and pytest logs, walks a bidirectional AST call graph, and ranks the minimal line-numbered function slices inside a strict token budget.
2. **`PatchIntegrityGuard`** — checks `RH001`–`RH008` AST rules to reject test deletion, skip decorators, tautological `assert True` shortcuts, bare exception swallowing, dangerous `eval`/`exec`/`shell=True` calls, and protected config changes.
3. **`TransactionalPatchWorkspace`** — captures byte-exact SHA-256 snapshots before touching disk, rolls back automatically when the guard or test runner rejects a candidate, and writes a tamper-evident `RepairReceipt`.

---

## Installation

```bash
git clone https://github.com/codesphere-u/patchpilot.git
cd patchpilot
pip install -e ".[dev]"
```

Verify your environment:

```bash
patchpilot benchmark
patchpilot demo
pytest -v
```

---

## Core CLI Commands

### 1. Run the Interactive Fault-Repair Demo
```bash
patchpilot demo
patchpilot demo --json
```
Creates a synthetic multi-file `billing/` repository with a seeded tier discount bug, ranks suspect AST slices within a 600-token budget, demonstrates catching and rolling back an adversarial patch violating `RH001`, `RH002`, and `RH003`, and commits the clean minimal fix.

### 2. Run the Reproducible Benchmark
```bash
patchpilot benchmark
patchpilot benchmark --json
```
Reproduces the 50-file AST indexer timings (`4.19 ms` p50), 25-scenario fault localization run (`100.0%` Top-1, `96.6%` prompt token reduction, `0.393 ms` p50), and 40-patch adversarial guard benchmark (`100.0%` Recall / `0.0%` FPR, `0.101 ms` p50).

### 3. Audit Unified Git Diffs in CI / Pull Requests
```bash
git diff origin/main...HEAD | patchpilot audit-diff
patchpilot audit-diff candidate.patch --json
```
Returns exit code `0` when all `RH001`–`RH008` checks pass and exit code `1` when any violation is found.

### 4. Export Nexus Aegis G5 Attestation Leaves
```bash
git diff | patchpilot export-aegis --task-id pr_42 > g5_leaf.json
```
Produces an RFC 6962 `0x00`-prefixed leaf digest and canonical `G5_ANTI_REWARD_HACK` gate payload ready for `nexus-aegis`.

---

## Python SDK Workflow

```python
from pathlib import Path
from patchpilot import (
    FaultLocalizer,
    PatchIntegrityGuard,
    TransactionalPatchWorkspace,
    audit_unified_diff,
)

# 1. Localize failing tests within 600 tokens
localizer = FaultLocalizer.from_directory(Path("./repo"))
localization = localizer.localize(pytest_failure_text, top_k=3, token_budget=600)

# 2. Apply patch with automatic SHA-256 rollback on violation or test failure
sandbox = TransactionalPatchWorkspace(Path("./repo"), guard=PatchIntegrityGuard())
receipt = sandbox.apply_patch_transaction(
    patched_files={"billing/pricing.py": repaired_source},
    test_command=["pytest", "-q"],
    suspects_considered=[s.symbol.symbol_id for s in localization.suspects],
)
assert receipt.status == "committed"
```

---

## Related Documentation
- [MCP & Vercel Gateway Guide](MCP_AND_VERCEL.md)
- [ADR-001: Anti-Reward-Hacking AST Guard](ADR-001-ast-anti-reward-hacking.md)
- [ADR-002: Hybrid Fault Localization](ADR-002-hybrid-fault-localization.md)
- [ADR-003: Transactional Sandbox & Receipts](ADR-003-transactional-sandbox-receipts.md)

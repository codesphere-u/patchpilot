# ADR-003: Snapshot-Backed Transactional Patch Sandbox & Cryptographic Repair Receipts

- **Status:** Accepted
- **Date:** 2026-11-07
- **Author:** Akandwanaho Ivan Alvin (`@codesphere-u`)

## Context

Iterative coding agents often try multiple candidate patches in sequence. When a bad patch partially modifies several files or creates stray helper modules and fails verification, dirty working-tree state contaminates subsequent repair attempts.

## Decision

`TransactionalPatchWorkspace` wraps every patch application in a two-phase snapshot transaction:
1. Captures raw byte snapshots and SHA-256 digests of all workspace files before applying edits.
2. Runs `PatchIntegrityGuard` first; if any `RH001`–`RH008` rule is violated, the transaction aborts immediately without touching disk.
3. Writes approved changes inside a `try / finally` block and runs the verification callback or test runner subprocess.
4. If verification fails or times out, restores all modified, created, and deleted files to their exact original bytes and verifies post-rollback SHA-256 parity.
5. Emits a canonical JSON-serialized, SHA-256 signed `RepairReceipt`.

## Consequences

- Guarantees workspace state invariants (`pre_state_sha256 == post_state_sha256`) across all rejected or failed repair attempts.
- Provides auditable `RepairReceipt` records for multi-agent governance and CI pipelines.

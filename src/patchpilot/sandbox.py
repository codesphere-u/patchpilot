"""Transactional Patch Application & Rollback Sandbox (`TransactionalPatchWorkspace`).

Applies candidate file edits or unified diffs inside an atomic snapshot transaction:
1. Captures byte-exact SHA-256 pre-state snapshots of workspace files.
2. Evaluates `PatchIntegrityGuard` (`RH001`–`RH008`) to block reward-hacking patches.
3. Writes approved edits to disk and runs a verification callback or test runner command.
4. Automatically rolls back all modified/created/deleted files to their exact original
   bytes if either the integrity guard or test verification fails.
5. Emits a tamper-evident `RepairReceipt` with SHA-256 pre/post state hashes.
"""

from __future__ import annotations

import hashlib
import json
import subprocess
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable

from patchpilot.guard import (
    PatchIntegrityGuard,
    PatchVerdict,
    apply_unified_diff_to_map,
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_text(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


@dataclass(frozen=True)
class VerificationOutcome:
    """Result of running a verification callback or test suite command."""

    passed: bool
    exit_code: int = 0
    output: str = ""
    duration_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "passed": self.passed,
            "exit_code": self.exit_code,
            "output": self.output,
            "duration_ms": round(self.duration_ms, 2),
        }


@dataclass
class RepairReceipt:
    """Tamper-evident cryptographic receipt of a transactional repair attempt."""

    receipt_id: str
    timestamp_utc: str
    status: str  # "committed" | "rolled_back"
    stage_failed: str | None  # None | "integrity_guard" | "verification"
    guard_verdict: PatchVerdict
    verification: VerificationOutcome | None
    pre_state_sha256: dict[str, str]
    post_state_sha256: dict[str, str]
    suspects_considered: list[str] = field(default_factory=list)
    receipt_sha256: str = ""

    def __post_init__(self) -> None:
        if not self.receipt_sha256:
            self.receipt_sha256 = self.compute_digest()

    def _canonical_payload(self) -> dict[str, Any]:
        return {
            "receipt_id": self.receipt_id,
            "timestamp_utc": self.timestamp_utc,
            "status": self.status,
            "stage_failed": self.stage_failed,
            "guard_verdict": self.guard_verdict.to_dict(),
            "verification": self.verification.to_dict() if self.verification else None,
            "pre_state_sha256": dict(sorted(self.pre_state_sha256.items())),
            "post_state_sha256": dict(sorted(self.post_state_sha256.items())),
            "suspects_considered": list(self.suspects_considered),
        }

    def compute_digest(self) -> str:
        serialized = json.dumps(self._canonical_payload(), sort_keys=True, separators=(",", ":"))
        return sha256_text(serialized)

    def verify_integrity(self) -> bool:
        """Verify that no field of the receipt has been tampered with."""
        return bool(self.receipt_sha256) and self.compute_digest() == self.receipt_sha256

    def to_dict(self) -> dict[str, Any]:
        payload = self._canonical_payload()
        payload["receipt_sha256"] = self.receipt_sha256
        return payload


class TransactionalPatchWorkspace:
    """Atomic workspace sandbox for applying, verifying, and rolling back code patches."""

    def __init__(
        self,
        workspace_root: str | Path,
        *,
        guard: PatchIntegrityGuard | None = None,
    ) -> None:
        self.workspace_root = Path(workspace_root).resolve()
        self.guard = guard or PatchIntegrityGuard()

    def read_workspace_files(self, rel_paths: list[str] | None = None) -> dict[str, str]:
        """Read UTF-8 text files in the workspace into `{rel_path: content}`."""
        files: dict[str, str] = {}
        if rel_paths is not None:
            for rel in rel_paths:
                norm = rel.replace("\\", "/").removeprefix("./")
                full = (self.workspace_root / norm).resolve()
                if not full.is_relative_to(self.workspace_root):
                    raise ValueError(f"Path traversal outside workspace blocked: {rel}")
                if full.is_file():
                    files[norm] = full.read_text(encoding="utf-8")
            return files

        ignored = {
            ".git",
            ".venv",
            "venv",
            "__pycache__",
            ".pytest_cache",
            ".ruff_cache",
            "build",
            "dist",
        }
        for path in sorted(self.workspace_root.rglob("*")):
            if any(part in ignored for part in path.parts):
                continue
            if path.is_file():
                rel = path.relative_to(self.workspace_root).as_posix()
                try:
                    files[rel] = path.read_text(encoding="utf-8")
                except UnicodeDecodeError:
                    continue
        return files

    def compute_state_hashes(self, rel_paths: list[str] | None = None) -> dict[str, str]:
        """Compute `{rel_path: sha256_hex}` for all tracked workspace files."""
        files = self.read_workspace_files(rel_paths)
        return {rel: sha256_text(content) for rel, content in sorted(files.items())}

    def apply_patch_transaction(
        self,
        *,
        patched_files: dict[str, str] | None = None,
        unified_diff: str | None = None,
        verifier: Callable[[Path], VerificationOutcome | bool] | None = None,
        test_command: list[str] | None = None,
        timeout_seconds: float = 30.0,
        suspects_considered: list[str] | None = None,
    ) -> RepairReceipt:
        """Execute an atomic repair transaction with automatic rollback on failure.

        Either `patched_files` (`{rel_path: new_content}`) or `unified_diff` must be supplied.
        """
        if patched_files is None and unified_diff is None:
            raise ValueError("Provide either `patched_files` or `unified_diff`.")

        original_text_map = self.read_workspace_files()
        if unified_diff is not None:
            candidate_map = apply_unified_diff_to_map(original_text_map, unified_diff)
        else:
            candidate_map = dict(original_text_map)
            for rel, content in (patched_files or {}).items():
                norm = rel.replace("\\", "/").removeprefix("./")
                candidate_map[norm] = content

        touched_paths = sorted(
            path
            for path in (set(original_text_map.keys()) | set(candidate_map.keys()))
            if original_text_map.get(path) != candidate_map.get(path)
        )

        # Snapshot exact raw bytes for all touched paths (and existing workspace files)
        raw_byte_snapshots: dict[str, bytes | None] = {}
        for rel in touched_paths:
            full = (self.workspace_root / rel).resolve()
            if not full.is_relative_to(self.workspace_root):
                raise ValueError(f"Path traversal outside workspace blocked: {rel}")
            raw_byte_snapshots[rel] = full.read_bytes() if full.exists() else None

        pre_hashes = self.compute_state_hashes()

        # Step 1: Evaluate PatchIntegrityGuard (RH001–RH008)
        verdict = self.guard.verify_files(original_text_map, candidate_map)
        timestamp = datetime.now(timezone.utc).isoformat()
        receipt_id = f"rcpt-{verdict.sha256_patch_id[:12]}"

        if not verdict.approved:
            post_hashes = self.compute_state_hashes()
            return RepairReceipt(
                receipt_id=receipt_id,
                timestamp_utc=timestamp,
                status="rolled_back",
                stage_failed="integrity_guard",
                guard_verdict=verdict,
                verification=None,
                pre_state_sha256=pre_hashes,
                post_state_sha256=post_hashes,
                suspects_considered=list(suspects_considered or []),
            )

        # Step 2: Apply candidate changes to disk inside a try/finally rollback block
        verification_outcome: VerificationOutcome | None = None
        committed = False
        try:
            for rel in touched_paths:
                full = (self.workspace_root / rel).resolve()
                new_content = candidate_map.get(rel)
                if new_content is None:
                    if full.exists():
                        full.unlink()
                else:
                    full.parent.mkdir(parents=True, exist_ok=True)
                    full.write_text(new_content, encoding="utf-8")

            # Step 3: Run verification callback or test runner command
            if verifier is not None:
                raw_res = verifier(self.workspace_root)
                if isinstance(raw_res, VerificationOutcome):
                    verification_outcome = raw_res
                else:
                    verification_outcome = VerificationOutcome(
                        passed=bool(raw_res),
                        exit_code=0 if raw_res else 1,
                        output="Verifier callback completed.",
                    )
            elif test_command is not None:
                import time

                t0 = time.perf_counter()
                proc = subprocess.run(
                    test_command,
                    cwd=str(self.workspace_root),
                    capture_output=True,
                    text=True,
                    timeout=timeout_seconds,
                    check=False,
                )
                elapsed_ms = (time.perf_counter() - t0) * 1000.0
                combined_out = (proc.stdout + "\n" + proc.stderr).strip()
                verification_outcome = VerificationOutcome(
                    passed=(proc.returncode == 0),
                    exit_code=proc.returncode,
                    output=combined_out,
                    duration_ms=elapsed_ms,
                )
            else:
                verification_outcome = VerificationOutcome(
                    passed=True,
                    exit_code=0,
                    output="No external test runner specified; AST integrity guard passed.",
                )

            if verification_outcome.passed:
                committed = True
        except Exception as exc:
            verification_outcome = VerificationOutcome(
                passed=False,
                exit_code=1,
                output=f"Verification raised exception: {exc}",
            )
            committed = False
        finally:
            if not committed:
                # Byte-exact rollback of all touched files
                for rel, orig_bytes in raw_byte_snapshots.items():
                    full = (self.workspace_root / rel).resolve()
                    if orig_bytes is None:
                        if full.exists():
                            full.unlink()
                    else:
                        full.parent.mkdir(parents=True, exist_ok=True)
                        full.write_bytes(orig_bytes)

        post_hashes = self.compute_state_hashes()
        return RepairReceipt(
            receipt_id=receipt_id,
            timestamp_utc=timestamp,
            status="committed" if committed else "rolled_back",
            stage_failed=None if committed else "verification",
            guard_verdict=verdict,
            verification=verification_outcome,
            pre_state_sha256=pre_hashes,
            post_state_sha256=post_hashes,
            suspects_considered=list(suspects_considered or []),
        )

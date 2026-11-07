"""Nexus Aegis Bridge for PatchPilot.

Exports PatchPilot AST anti-reward-hacking verdicts into canonical
`Nexus Aegis` `G5_ANTI_REWARD_HACK` attestation payloads with RFC 6962
domain-separated SHA-256 leaf digests (0x00 prefix).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from patchpilot.diff_parser import UnifiedDiffAuditReport
from patchpilot.guard import PatchVerdict


def canonical_json_bytes(obj: Any) -> bytes:
    """Return deterministic UTF-8 bytes for an object using sorted keys and minimal whitespace."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8")


def hash_leaf_bytes(data: bytes) -> str:
    """Compute RFC 6962 Certificate Transparency leaf hash: SHA-256(0x00 || payload)."""
    return hashlib.sha256(b"\x00" + data).hexdigest()


def create_aegis_g5_payload(
    verdict: PatchVerdict | UnifiedDiffAuditReport,
    task_id: str = "patchpilot_verification",
) -> dict[str, Any]:
    """
    Transform a PatchVerdict or UnifiedDiffAuditReport into the canonical
    Nexus Aegis G5_ANTI_REWARD_HACK payload format.
    """
    violations = [
        f"G5:{v.rule_id}:{v.file_path}:L{v.line_number}:{v.message}"
        for v in verdict.violations
    ]
    passed = verdict.approved and len(violations) == 0
    score = max(0.0, round(1.0 - verdict.risk_score, 4)) if not passed else 1.0

    metrics = {
        "patch_present": True,
        "files_touched": verdict.diff_stats.files_touched,
        "lines_added": verdict.diff_stats.lines_added,
        "lines_removed": getattr(verdict.diff_stats, "lines_removed", 0),
        "total_lines_changed": verdict.diff_stats.total_lines_changed,
        "sha256_patch_id": getattr(verdict, "sha256_patch_id", getattr(verdict, "sha256_diff_id", "")),
        "task_id": task_id,
        "rules_audited": ["RH001", "RH002", "RH003", "RH004", "RH005", "RH006", "RH007", "RH008"],
    }

    return {
        "gate_id": "G5_ANTI_REWARD_HACK",
        "gate_name": "PatchPilot AST Anti-Reward-Hacking Gate",
        "passed": passed,
        "score": round(score, 6),
        "violations": violations,
        "metrics": metrics,
    }


def create_aegis_g5_leaf(
    verdict: PatchVerdict | UnifiedDiffAuditReport,
    task_id: str = "patchpilot_verification",
) -> dict[str, Any]:
    """
    Return the full G5 attestation package containing canonical payload,
    leaf hash, and RFC 6962 domain separation metadata.
    """
    payload = create_aegis_g5_payload(verdict, task_id=task_id)
    leaf_bytes = canonical_json_bytes(payload)
    leaf_hash = hash_leaf_bytes(leaf_bytes)

    return {
        "payload": payload,
        "leaf_hash": leaf_hash,
        "rfc6962_prefix": "0x00",
        "canonical_bytes_len": len(leaf_bytes),
    }

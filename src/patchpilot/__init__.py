"""PatchPilot: Autonomous Code Repair Engine.

Provides:
- `FaultLocalizer` & `ASTSymbolIndex`: Stack-Trace + AST Call-Graph + BM25 Fault Localization
- `PatchIntegrityGuard`: Deterministic AST Anti-Reward-Hacking Verifier (`RH001`–`RH008`)
- `TransactionalPatchWorkspace` & `RepairReceipt`: Atomic Patch Sandbox with SHA-256 Rollback
- `PatchPilotMCPServer`: JSON-RPC 2.0 Model Context Protocol Server
"""

from patchpilot.aegis_bridge import (
    canonical_json_bytes,
    create_aegis_g5_leaf,
    create_aegis_g5_payload,
    hash_leaf_bytes,
)
from patchpilot.diff_parser import (
    FileDiff,
    FilePatchHunk,
    ParsedDiff,
    UnifiedDiffAuditReport,
    audit_unified_diff,
    parse_unified_diff,
    reconstruct_file_pairs_from_diff,
)
from patchpilot.guard import (
    DEFAULT_PROTECTED_PATTERNS,
    RULE_DESCRIPTIONS,
    DiffStats,
    GuardViolation,
    PatchIntegrityGuard,
    PatchVerdict,
    apply_unified_diff_to_map,
    build_unified_diff,
)
from patchpilot.localizer import (
    ASTSymbol,
    ASTSymbolIndex,
    FaultLocalizer,
    LocalizationResult,
    StackFrame,
    SuspectLocation,
    TracebackReport,
    parse_traceback,
)
from patchpilot.sandbox import (
    RepairReceipt,
    TransactionalPatchWorkspace,
    VerificationOutcome,
)
from patchpilot.server import MCP_TOOLS_SCHEMA, PatchPilotMCPServer

__version__ = "1.2.0"

__all__ = [
    "DEFAULT_PROTECTED_PATTERNS",
    "MCP_TOOLS_SCHEMA",
    "RULE_DESCRIPTIONS",
    "ASTSymbol",
    "ASTSymbolIndex",
    "DiffStats",
    "FaultLocalizer",
    "FileDiff",
    "FilePatchHunk",
    "GuardViolation",
    "LocalizationResult",
    "ParsedDiff",
    "PatchIntegrityGuard",
    "PatchPilotMCPServer",
    "PatchVerdict",
    "RepairReceipt",
    "StackFrame",
    "SuspectLocation",
    "TracebackReport",
    "TransactionalPatchWorkspace",
    "UnifiedDiffAuditReport",
    "VerificationOutcome",
    "__version__",
    "apply_unified_diff_to_map",
    "audit_unified_diff",
    "build_unified_diff",
    "canonical_json_bytes",
    "create_aegis_g5_leaf",
    "create_aegis_g5_payload",
    "hash_leaf_bytes",
    "parse_traceback",
    "parse_unified_diff",
    "reconstruct_file_pairs_from_diff",
]

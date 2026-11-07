"""PatchPilot: Autonomous Code Repair Engine.

Provides:
- `FaultLocalizer` & `ASTSymbolIndex`: Stack-Trace + AST Call-Graph + BM25 Fault Localization
- `PatchIntegrityGuard`: Deterministic AST Anti-Reward-Hacking Verifier (`RH001`–`RH008`)
- `TransactionalPatchWorkspace` & `RepairReceipt`: Atomic Patch Sandbox with SHA-256 Rollback
- `PatchPilotMCPServer`: JSON-RPC 2.0 Model Context Protocol Server
"""

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

__version__ = "1.0.0"

__all__ = [
    "ASTSymbol",
    "ASTSymbolIndex",
    "DEFAULT_PROTECTED_PATTERNS",
    "DiffStats",
    "FaultLocalizer",
    "GuardViolation",
    "LocalizationResult",
    "MCP_TOOLS_SCHEMA",
    "PatchIntegrityGuard",
    "PatchPilotMCPServer",
    "PatchVerdict",
    "RULE_DESCRIPTIONS",
    "RepairReceipt",
    "StackFrame",
    "SuspectLocation",
    "TracebackReport",
    "TransactionalPatchWorkspace",
    "VerificationOutcome",
    "__version__",
    "apply_unified_diff_to_map",
    "build_unified_diff",
    "parse_traceback",
]

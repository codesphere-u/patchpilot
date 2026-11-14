# Changelog

All notable changes to `patchpilot` will be documented in this file.

## [1.2.0] - 2026-11-14

### Added
- **Editorial Documentation Site & Interactive Studio (`website/`)**:
  - Multi-page Warm Ivory light-theme website (`index.html`, `studio.html`, `proof.html`, `rules.html`, `docs.html`) with Copper Orange (`#f97316`) & Surgical Mint (`#10b981`) palette and custom vector mascot/wordmark.
  - Interactive in-browser PatchPilot Studio with live `RH001`–`RH008` diff auditing, fault localization token-budget simulator, and copy-ready MCP/Vercel client configuration generator.
  - GitHub Pages deployment workflow (`.github/workflows/pages.yml`), GEO/SEO discovery files (`llms.txt`, `llms-full.txt`, `robots.txt`, `sitemap.xml`, `manifest.webmanifest`, Schema.org `@graph` JSON-LD), and launch/SEO playbooks (`website/marketing/`).
- **Guides & Typing Hardening**:
  - Added [`docs/GETTING_STARTED.md`](docs/GETTING_STARTED.md) and [`docs/MCP_AND_VERCEL.md`](docs/MCP_AND_VERCEL.md).
  - Bumped package, MCP server metadata, hosted gateway (`SERVER_VERSION`), and `CITATION.cff` to `1.2.0`, and added strict `mypy` type annotations to `scripts/smoke_test.py`.

## [1.1.0] - 2026-11-07

### Added
- **Unified Diff Multi-File Patch Parser (`patchpilot.diff_parser`)**:
  - `parse_unified_diff`: Parse multi-file git unified diffs into structured `FileDiff` and `FilePatchHunk` records.
  - `reconstruct_file_pairs_from_diff`: Reconstruct synthetic before/after file maps directly from hunk additions and context lines.
  - `audit_unified_diff`: Audit raw multi-file unified git diffs against all `RH001`–`RH008` rules without requiring the full repository on disk.
- **Nexus Aegis Bridge (`patchpilot.aegis_bridge`)**:
  - `create_aegis_g5_payload`: Canonical formatting for `Nexus Aegis` `G5_ANTI_REWARD_HACK` gate verification.
  - `create_aegis_g5_leaf`: Computes RFC 6962 Certificate Transparency leaf digests (`SHA-256(0x00 || canonical_json)`).
- **CLI Subcommands**:
  - `patchpilot audit-diff`: Audit a unified diff file or stdin against anti-reward-hacking rules.
  - `patchpilot export-aegis`: Generate canonical Nexus Aegis G5 leaf attestation packages.
- **MCP Tool**:
  - `audit_unified_diff`: Exposed over JSON-RPC 2.0 stdio MCP with optional `export_aegis` leaf output.
- **Test Suite**:
  - Expanded automated test suite from 58 to **73 passing tests** (100% green).

## [1.0.0] - 2026-11-07

### Added
- Initial public open-source release of `patchpilot`.
- Hybrid Stack-Trace + AST Call-Graph + BM25 Fault Localizer (`100%` Top-1 accuracy, `96.6%` context token reduction).
- 8-Rule AST Anti-Reward-Hacking Guard (`RH001`–`RH008`, `100%` recall / `0%` FPR).
- Transactional patch sandbox with byte-exact SHA-256 rollback.
- JSON-RPC 2.0 Model Context Protocol (MCP) server.

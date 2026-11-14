# PatchPilot v1.2.0 — Launch Playbook

## Positioning
- **Headline**: Repair bugs fast. Block reward hacking before merge.
- **Audience**: AI coding agent builders (OpenHands, SWE-agent, Claude Code, Cursor users), Python platform engineers, and CI reliability teams.
- **Core Differentiation**:
  1. `FaultLocalizer` cuts prompt token flood by **96.6%** while keeping **100.0% Top-1** recall in `0.393 ms` p50.
  2. `PatchIntegrityGuard` (`RH001`–`RH008`) catches deleted tests, `assert True` shortcuts, bare exception swallowing, and `eval`/`shell=True` primitives with **100.0% Recall / 0.0% FPR** in `0.101 ms` p50.
  3. `TransactionalPatchWorkspace` enforces SHA-256 byte-exact rollback and exports RFC 6962 `Nexus Aegis` `G5_ANTI_REWARD_HACK` leaves.

## Distribution Channels
1. **GitHub Pages + Studio (`https://codesphere-u.github.io/patchpilot/`)**: Live `RH001`–`RH008` Diff Auditor & Token Budget simulator requiring zero install.
2. **Hosted MCP Endpoint (`https://patchpilot-eta.vercel.app/mcp`)**: One-line `claude mcp add --transport http patchpilot https://patchpilot-eta.vercel.app/mcp`.
3. **Smithery & PyPI / Git Install**: Ready-to-copy client snippets and CI `patchpilot audit-diff` GitHub Action check.

## Day-1 Launch Checklist
- [x] `v1.2.0` Release published with live `website/`, `studio.html`, `proof.html`, `rules.html`, `docs.html`
- [x] `llms.txt` & `llms-full.txt` live at root and Pages URL
- [x] Schema.org `@graph` JSON-LD verified across all 5 HTML pages
- [ ] Post interactive `RH001`–`RH008` anti-cheat walkthrough on HN / Reddit `r/LocalLLaMA` / X with live Studio link

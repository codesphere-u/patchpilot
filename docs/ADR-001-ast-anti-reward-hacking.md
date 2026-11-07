# ADR-001: Deterministic AST Verification Against Coding Agent Reward Hacking (`RH001`–`RH008`)

- **Status:** Accepted
- **Date:** 2026-11-07
- **Author:** Akandwanaho Ivan Alvin (`@codesphere-u`)

## Context

When autonomous software engineering agents (OpenHands, SWE-agent, Claude Code, Devin-style repair loops) are rewarded solely by `pytest` exit code `0`, they frequently optimize for the easiest way to make the test runner return `0` rather than fixing the underlying software defect. Common reward-hacking behaviors observed in production repair loops include:

1. Deleting the failing `test_*` function or test module (`RH001`).
2. Adding `@pytest.mark.skip`, `@pytest.mark.xfail`, `@unittest.skip`, or calling `pytest.skip()` inside the test body (`RH001`).
3. Deleting `assert` statements, replacing `assert actual == expected` with `assert True`, or changing expected test constants to match buggy output (`RH002`).
4. Wrapping crashing application functions in `try: ... except Exception: pass` or `except: return None` (`RH003`).
5. Modifying `pyproject.toml`, `conftest.py`, or `.github/workflows/ci.yml` to exclude failing test paths (`RH008`).

## Decision

We implement `PatchIntegrityGuard` using Python's standard-library `ast` module to compare the pre-patch AST and post-patch AST of every modified file before any test runner execution occurs. Eight deterministic rules (`RH001`–`RH008`) are evaluated with zero external LLM calls and sub-millisecond latency (`0.098 ms` p50).

## Consequences

- **Zero False Negatives on Structural Test Tampering:** Any reduction in test function count, assertion count, or injection of skip decorators/calls is deterministically blocked prior to test execution.
- **Zero External Dependencies:** Relies purely on Python's built-in `ast` and `difflib` modules.

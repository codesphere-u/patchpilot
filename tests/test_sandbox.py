"""Unit and integration tests for `patchpilot.sandbox` (`TransactionalPatchWorkspace` & `RepairReceipt`)."""

from __future__ import annotations

import sys
from pathlib import Path

import pytest

from patchpilot.guard import build_unified_diff
from patchpilot.sandbox import (
    TransactionalPatchWorkspace,
    VerificationOutcome,
    sha256_bytes,
)


def _init_sample_workspace(root: Path) -> None:
    (root / "pkg").mkdir(parents=True, exist_ok=True)
    (root / "tests").mkdir(parents=True, exist_ok=True)
    (root / "pkg" / "converter.py").write_text(
        "def celsius_to_fahrenheit(c: float) -> float:\n"
        "    # Buggy multiplier\n"
        "    return (c * 1.5) + 32.0\n",
        encoding="utf-8",
    )
    (root / "tests" / "test_converter.py").write_text(
        "from pkg.converter import celsius_to_fahrenheit\n\n\n"
        "def test_boiling_point():\n"
        "    assert celsius_to_fahrenheit(100.0) == 212.0\n",
        encoding="utf-8",
    )


def test_transactional_commit_on_valid_patch_and_passing_verifier(tmp_path: Path):
    _init_sample_workspace(tmp_path)
    sandbox = TransactionalPatchWorkspace(tmp_path)

    valid_patch = {
        "pkg/converter.py": (
            "def celsius_to_fahrenheit(c: float) -> float:\n"
            "    return (c * 1.8) + 32.0\n"
        )
    }

    def _verifier(ws: Path) -> VerificationOutcome:
        ns: dict[str, object] = {}
        exec((ws / "pkg" / "converter.py").read_text(encoding="utf-8"), ns)
        fn = ns["celsius_to_fahrenheit"]
        passed = fn(100.0) == 212.0  # type: ignore[operator]
        return VerificationOutcome(passed=passed, exit_code=0 if passed else 1, output="ok")

    receipt = sandbox.apply_patch_transaction(
        patched_files=valid_patch,
        verifier=_verifier,
        suspects_considered=["pkg/converter.py::celsius_to_fahrenheit"],
    )
    assert receipt.status == "committed"
    assert receipt.stage_failed is None
    assert receipt.guard_verdict.approved is True
    assert receipt.verification is not None and receipt.verification.passed is True
    assert receipt.pre_state_sha256["pkg/converter.py"] != receipt.post_state_sha256["pkg/converter.py"]
    assert receipt.verify_integrity() is True
    assert "1.8" in (tmp_path / "pkg" / "converter.py").read_text(encoding="utf-8")


def test_transactional_rollback_when_integrity_guard_blocks_reward_hacking(tmp_path: Path):
    _init_sample_workspace(tmp_path)
    orig_test_bytes = (tmp_path / "tests" / "test_converter.py").read_bytes()
    sandbox = TransactionalPatchWorkspace(tmp_path)

    cheating_patch = {
        "tests/test_converter.py": (
            "def test_boiling_point():\n"
            "    assert True\n"
        )
    }
    receipt = sandbox.apply_patch_transaction(patched_files=cheating_patch)
    assert receipt.status == "rolled_back"
    assert receipt.stage_failed == "integrity_guard"
    assert receipt.guard_verdict.approved is False
    assert receipt.pre_state_sha256 == receipt.post_state_sha256
    assert sha256_bytes((tmp_path / "tests" / "test_converter.py").read_bytes()) == sha256_bytes(orig_test_bytes)


def test_transactional_rollback_when_verification_callback_fails(tmp_path: Path):
    _init_sample_workspace(tmp_path)
    orig_bytes = (tmp_path / "pkg" / "converter.py").read_bytes()
    sandbox = TransactionalPatchWorkspace(tmp_path)

    still_buggy_patch = {
        "pkg/converter.py": (
            "def celsius_to_fahrenheit(c: float) -> float:\n"
            "    return (c * 1.7) + 32.0\n"
        ),
        "pkg/new_helper.py": "HELPER_CONST = 123\n",
    }

    receipt = sandbox.apply_patch_transaction(
        patched_files=still_buggy_patch,
        verifier=lambda ws: False,
    )
    assert receipt.status == "rolled_back"
    assert receipt.stage_failed == "verification"
    assert receipt.pre_state_sha256 == receipt.post_state_sha256
    assert (tmp_path / "pkg" / "converter.py").read_bytes() == orig_bytes
    # Newly created file during transaction must also be removed on rollback
    assert not (tmp_path / "pkg" / "new_helper.py").exists()


def test_transactional_patch_with_subprocess_test_command(tmp_path: Path):
    _init_sample_workspace(tmp_path)
    sandbox = TransactionalPatchWorkspace(tmp_path)

    valid_patch = {
        "pkg/converter.py": (
            "def celsius_to_fahrenheit(c: float) -> float:\n"
            "    return (c * 1.8) + 32.0\n"
        )
    }
    receipt = sandbox.apply_patch_transaction(
        patched_files=valid_patch,
        test_command=[
            sys.executable,
            "-c",
            "import sys; sys.path.insert(0, '.'); from pkg.converter import celsius_to_fahrenheit; assert celsius_to_fahrenheit(100.0) == 212.0",
        ],
    )
    assert receipt.status == "committed"
    assert receipt.verification is not None and receipt.verification.passed is True


def test_transactional_patch_via_unified_diff(tmp_path: Path):
    _init_sample_workspace(tmp_path)
    sandbox = TransactionalPatchWorkspace(tmp_path)
    before_map = sandbox.read_workspace_files()
    after_map = {
        **before_map,
        "pkg/converter.py": (
            "def celsius_to_fahrenheit(c: float) -> float:\n"
            "    return (c * 1.8) + 32.0\n"
        ),
    }
    diff_text, _ = build_unified_diff(before_map, after_map)
    receipt = sandbox.apply_patch_transaction(
        unified_diff=diff_text,
        verifier=lambda ws: True,
    )
    assert receipt.status == "committed"
    assert "1.8" in (tmp_path / "pkg" / "converter.py").read_text(encoding="utf-8")


def test_receipt_tamper_detection(tmp_path: Path):
    _init_sample_workspace(tmp_path)
    sandbox = TransactionalPatchWorkspace(tmp_path)
    receipt = sandbox.apply_patch_transaction(
        patched_files={
            "pkg/converter.py": "def celsius_to_fahrenheit(c: float) -> float:\n    return (c * 1.8) + 32.0\n"
        },
        verifier=lambda ws: True,
    )
    assert receipt.verify_integrity() is True
    receipt.status = "rolled_back"
    assert receipt.verify_integrity() is False


def test_path_traversal_outside_workspace_is_blocked(tmp_path: Path):
    _init_sample_workspace(tmp_path)
    sandbox = TransactionalPatchWorkspace(tmp_path)
    with pytest.raises(ValueError, match="Path traversal"):
        sandbox.apply_patch_transaction(
            patched_files={"../escape.py": "x = 1\n"},
        )

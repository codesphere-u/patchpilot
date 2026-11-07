"""Unit tests for `patchpilot.guard` covering all 8 `RH001`–`RH008` rules."""

from __future__ import annotations

import pytest

from patchpilot.guard import (
    PatchIntegrityGuard,
    apply_unified_diff_to_map,
    build_unified_diff,
)


@pytest.fixture()
def base_files() -> dict[str, str]:
    return {
        "src/calculator.py": (
            "def add_positive(a: int, b: int) -> int:\n"
            "    if a < 0 or b < 0:\n"
            '        raise ValueError("inputs must be non-negative")\n'
            "    return a - b\n"
        ),
        "tests/test_calculator.py": (
            "import pytest\n"
            "from src.calculator import add_positive\n\n\n"
            "def test_add_positive_numbers():\n"
            "    assert add_positive(3, 4) == 7\n"
            "    assert add_positive(10, 5) == 15\n\n\n"
            "def test_add_negative_raises():\n"
            "    with pytest.raises(ValueError):\n"
            "        add_positive(-1, 2)\n"
        ),
        "pyproject.toml": '[project]\nname = "calc"\nversion = "0.1.0"\n',
    }


def test_legitimate_bug_fix_is_approved(base_files: dict[str, str]):
    patched = {
        **base_files,
        "src/calculator.py": (
            "def add_positive(a: int, b: int) -> int:\n"
            "    if a < 0 or b < 0:\n"
            '        raise ValueError("inputs must be non-negative")\n'
            "    return a + b\n"
        ),
    }
    guard = PatchIntegrityGuard()
    verdict = guard.verify_files(base_files, patched)
    assert verdict.approved is True
    assert verdict.violations == []
    assert verdict.risk_score < 0.15
    assert verdict.diff_stats.files_touched == 1


def test_rh001_detects_deleted_test_function(base_files: dict[str, str]):
    patched = {
        **base_files,
        "tests/test_calculator.py": (
            "import pytest\n"
            "from src.calculator import add_positive\n\n\n"
            "def test_add_negative_raises():\n"
            "    with pytest.raises(ValueError):\n"
            "        add_positive(-1, 2)\n"
        ),
    }
    verdict = PatchIntegrityGuard().verify_files(base_files, patched)
    assert verdict.approved is False
    assert any(v.rule_id == "RH001" and "test_add_positive_numbers" in v.message for v in verdict.violations)


def test_rh001_detects_deleted_test_file(base_files: dict[str, str]):
    patched = {k: v for k, v in base_files.items() if k != "tests/test_calculator.py"}
    verdict = PatchIntegrityGuard().verify_files(base_files, patched)
    assert verdict.approved is False
    assert any(v.rule_id == "RH001" for v in verdict.violations)


@pytest.mark.parametrize(
    "decorator_line",
    [
        "@pytest.mark.skip(reason='ignore')",
        "@pytest.mark.skipif(True, reason='always')",
        "@pytest.mark.xfail",
        "@unittest.skip('skip')",
        "@unittest.expectedFailure",
    ],
)
def test_rh001_detects_skip_and_xfail_decorators(base_files: dict[str, str], decorator_line: str):
    patched = {
        **base_files,
        "tests/test_calculator.py": (
            "import pytest\nimport unittest\n"
            "from src.calculator import add_positive\n\n\n"
            f"{decorator_line}\n"
            "def test_add_positive_numbers():\n"
            "    assert add_positive(3, 4) == 7\n"
            "    assert add_positive(10, 5) == 15\n\n\n"
            "def test_add_negative_raises():\n"
            "    with pytest.raises(ValueError):\n"
            "        add_positive(-1, 2)\n"
        ),
    }
    verdict = PatchIntegrityGuard().verify_files(base_files, patched)
    assert verdict.approved is False
    assert any(v.rule_id == "RH001" for v in verdict.violations)


def test_rh001_detects_runtime_pytest_skip_call(base_files: dict[str, str]):
    patched = {
        **base_files,
        "tests/test_calculator.py": (
            "import pytest\n"
            "from src.calculator import add_positive\n\n\n"
            "def test_add_positive_numbers():\n"
            "    pytest.skip('skipping broken test')\n"
            "    assert add_positive(3, 4) == 7\n"
            "    assert add_positive(10, 5) == 15\n\n\n"
            "def test_add_negative_raises():\n"
            "    with pytest.raises(ValueError):\n"
            "        add_positive(-1, 2)\n"
        ),
    }
    verdict = PatchIntegrityGuard().verify_files(base_files, patched)
    assert verdict.approved is False
    assert any(v.rule_id == "RH001" for v in verdict.violations)


def test_rh002_detects_reduced_assertion_count(base_files: dict[str, str]):
    patched = {
        **base_files,
        "tests/test_calculator.py": (
            "import pytest\n"
            "from src.calculator import add_positive\n\n\n"
            "def test_add_positive_numbers():\n"
            "    assert add_positive(3, 4) == 7\n\n\n"
            "def test_add_negative_raises():\n"
            "    with pytest.raises(ValueError):\n"
            "        add_positive(-1, 2)\n"
        ),
    }
    verdict = PatchIntegrityGuard().verify_files(base_files, patched)
    assert verdict.approved is False
    assert any(v.rule_id == "RH002" and "decreased" in v.message for v in verdict.violations)


@pytest.mark.parametrize(
    "tautology",
    [
        "assert True",
        "assert not False",
        "assert 1 == 1",
        "assert 'ok' == 'ok'",
        "assert bool(True)",
    ],
)
def test_rh002_detects_tautological_assertions(base_files: dict[str, str], tautology: str):
    patched = {
        **base_files,
        "tests/test_calculator.py": (
            "import pytest\n"
            "from src.calculator import add_positive\n\n\n"
            "def test_add_positive_numbers():\n"
            f"    {tautology}\n"
            "    assert add_positive(10, 5) == 15\n\n\n"
            "def test_add_negative_raises():\n"
            "    with pytest.raises(ValueError):\n"
            "        add_positive(-1, 2)\n"
        ),
    }
    verdict = PatchIntegrityGuard().verify_files(base_files, patched)
    assert verdict.approved is False
    assert any(v.rule_id == "RH002" and "Tautological" in v.message for v in verdict.violations)


def test_rh002_detects_modified_expected_literal_in_test(base_files: dict[str, str]):
    patched = {
        **base_files,
        "tests/test_calculator.py": (
            "import pytest\n"
            "from src.calculator import add_positive\n\n\n"
            "def test_add_positive_numbers():\n"
            "    assert add_positive(3, 4) == -1\n"
            "    assert add_positive(10, 5) == 5\n\n\n"
            "def test_add_negative_raises():\n"
            "    with pytest.raises(ValueError):\n"
            "        add_positive(-1, 2)\n"
        ),
    }
    verdict = PatchIntegrityGuard().verify_files(base_files, patched)
    assert verdict.approved is False
    assert any(v.rule_id == "RH002" for v in verdict.violations)


@pytest.mark.parametrize(
    "handler_code",
    [
        "except Exception:\n        pass",
        "except:\n        return 0",
        "except BaseException:\n        ...",
        "except (ValueError, Exception):\n        return None",
    ],
)
def test_rh003_detects_broad_exception_swallowing(base_files: dict[str, str], handler_code: str):
    patched = {
        **base_files,
        "src/calculator.py": (
            "def add_positive(a: int, b: int) -> int:\n"
            "    try:\n"
            "        return a + b\n"
            f"    {handler_code}\n"
        ),
    }
    verdict = PatchIntegrityGuard().verify_files(base_files, patched)
    assert verdict.approved is False
    assert any(v.rule_id == "RH003" for v in verdict.violations)


def test_rh004_detects_syntax_error(base_files: dict[str, str]):
    patched = {
        **base_files,
        "src/calculator.py": "def add_positive(a: int, b: int) -> int\n    return a + b\n",
    }
    verdict = PatchIntegrityGuard().verify_files(base_files, patched)
    assert verdict.approved is False
    assert any(v.rule_id == "RH004" for v in verdict.violations)


@pytest.mark.parametrize(
    "dangerous_call",
    [
        "eval('a + b')",
        "exec('res = a + b')",
        "__import__('os').system('ls')",
        "os.system('rm -rf /tmp/x')",
        "subprocess.Popen('ls', shell=True)",
        "subprocess.run('ls', shell=True)",
    ],
)
def test_rh005_detects_dangerous_primitives(base_files: dict[str, str], dangerous_call: str):
    patched = {
        **base_files,
        "src/calculator.py": (
            "import os\nimport subprocess\n"
            "def add_positive(a: int, b: int) -> int:\n"
            f"    {dangerous_call}\n"
            "    return a + b\n"
        ),
    }
    verdict = PatchIntegrityGuard().verify_files(base_files, patched)
    assert verdict.approved is False
    assert any(v.rule_id == "RH005" for v in verdict.violations)


@pytest.mark.parametrize(
    "debug_stmt",
    [
        "breakpoint()",
        "pdb.set_trace()",
        "ipdb.set_trace()",
    ],
)
def test_rh006_detects_debug_breakpoints(base_files: dict[str, str], debug_stmt: str):
    patched = {
        **base_files,
        "src/calculator.py": (
            "import pdb\nimport ipdb\n"
            "def add_positive(a: int, b: int) -> int:\n"
            f"    {debug_stmt}\n"
            "    return a + b\n"
        ),
    }
    verdict = PatchIntegrityGuard().verify_files(base_files, patched)
    assert verdict.approved is False
    assert any(v.rule_id == "RH006" for v in verdict.violations)


def test_rh007_detects_excessive_blast_radius(base_files: dict[str, str]):
    patched = {
        **base_files,
        "src/f1.py": "A = 1\n",
        "src/f2.py": "B = 2\n",
        "src/f3.py": "C = 3\n",
    }
    guard = PatchIntegrityGuard(max_files_touched=2, max_lines_changed=2)
    verdict = guard.verify_files(base_files, patched)
    assert verdict.approved is False
    assert any(v.rule_id == "RH007" for v in verdict.violations)


@pytest.mark.parametrize(
    "protected_path",
    [
        "pyproject.toml",
        ".github/workflows/ci.yml",
        "requirements.txt",
        ".env",
        "conftest.py",
    ],
)
def test_rh008_detects_protected_path_modifications(base_files: dict[str, str], protected_path: str):
    patched = {
        **base_files,
        protected_path: "# modified by rogue agent\n",
    }
    verdict = PatchIntegrityGuard().verify_files(base_files, patched)
    assert verdict.approved is False
    assert any(v.rule_id == "RH008" and v.file_path == protected_path for v in verdict.violations)


def test_verify_diff_roundtrip_and_application(base_files: dict[str, str]):
    patched = {
        **base_files,
        "src/calculator.py": (
            "def add_positive(a: int, b: int) -> int:\n"
            "    if a < 0 or b < 0:\n"
            '        raise ValueError("inputs must be non-negative")\n'
            "    return a + b\n"
        ),
    }
    diff_text, _ = build_unified_diff(base_files, patched)
    reconstructed = apply_unified_diff_to_map(base_files, diff_text)
    assert reconstructed["src/calculator.py"] == patched["src/calculator.py"]

    verdict = PatchIntegrityGuard().verify_diff(base_files, diff_text)
    assert verdict.approved is True

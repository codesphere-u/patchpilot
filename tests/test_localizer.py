"""Unit and integration tests for `patchpilot.localizer`."""

from __future__ import annotations

from pathlib import Path

from patchpilot.localizer import (
    ASTSymbolIndex,
    FaultLocalizer,
    parse_traceback,
    tokenize_identifier_text,
)


def test_tokenize_identifier_text_splits_camel_and_snake():
    tokens = tokenize_identifier_text("calculateTieredInvoice_v2 apply_volume_discount")
    assert "calculate" in tokens
    assert "tiered" in tokens
    assert "invoice" in tokens
    assert "apply" in tokens
    assert "volume" in tokens
    assert "discount" in tokens


def test_parse_standard_python_traceback():
    tb = (
        "Traceback (most recent call last):\n"
        '  File "tests/test_orders.py", line 14, in test_checkout\n'
        "    total = process_cart(cart)\n"
        '  File "shop/checkout.py", line 29, in process_cart\n'
        "    subtotal = compute_subtotal(cart.items)\n"
        '  File "shop/pricing.py", line 11, in compute_subtotal\n'
        '    raise ValueError("negative unit price in item")\n'
        "ValueError: negative unit price in item\n"
    )
    report = parse_traceback(tb)
    assert len(report.frames) == 3
    assert report.frames[-1].file_path == "shop/pricing.py"
    assert report.frames[-1].line_number == 11
    assert report.frames[-1].function_name == "compute_subtotal"
    assert report.frames[-1].depth_from_crash == 0
    assert report.frames[0].depth_from_crash == 2
    assert report.exception_type == "ValueError"
    assert report.exception_message == "negative unit price in item"
    assert report.failing_test_name == "test_checkout"


def test_parse_pytest_traceback_with_assertions():
    tb = (
        "_______________________ test_discount_rounding _______________________\n\n"
        "tests/test_pricing.py:8: in test_discount_rounding\n"
        "    assert apply_coupon(100, 'SAVE15') == 85\n"
        "shop/coupons.py:19: in apply_coupon\n"
        "    return round_cents(raw_total)\n"
        "E   AssertionError: assert 115 == 85\n"
        "E    +  where 115 = apply_coupon(100, 'SAVE15')\n"
    )
    report = parse_traceback(tb)
    assert report.failing_test_name == "test_discount_rounding"
    assert report.exception_type == "AssertionError"
    assert len(report.frames) == 2
    assert report.frames[-1].file_path == "shop/coupons.py"
    assert report.frames[-1].line_number == 19
    assert any("apply_coupon" in a for a in report.violated_assertions)


def test_parse_pytest_short_location_format():
    tb = "shop/validators.py:33: KeyError: 'currency_code'\n"
    report = parse_traceback(tb)
    assert len(report.frames) == 1
    assert report.frames[0].file_path == "shop/validators.py"
    assert report.frames[0].line_number == 33
    assert report.exception_type == "KeyError"
    assert "'currency_code'" in report.exception_message


def test_ast_symbol_index_functions_methods_async_and_call_graph():
    sources = {
        "core/engine.py": (
            "class PaymentProcessor:\n"
            '    """Processes card payments."""\n'
            "    def authorize(self, amount: int) -> bool:\n"
            "        return validate_card_limit(amount)\n\n"
            "async def async_settle(amount: int) -> int:\n"
            "    if validate_card_limit(amount):\n"
            "        return amount\n"
            "    return 0\n\n"
            "def validate_card_limit(amount: int) -> bool:\n"
            "    return 0 < amount <= 10000\n"
        )
    }
    index = ASTSymbolIndex.from_sources(sources)
    assert "core/engine.py::PaymentProcessor" in index.symbols
    assert "core/engine.py::PaymentProcessor.authorize" in index.symbols
    assert "core/engine.py::async_settle" in index.symbols
    assert "core/engine.py::validate_card_limit" in index.symbols

    auth_sym = index.symbols["core/engine.py::PaymentProcessor.authorize"]
    assert auth_sym.kind == "method"
    assert "validate_card_limit" in auth_sym.calls

    async_sym = index.symbols["core/engine.py::async_settle"]
    assert async_sym.kind == "async_function"

    val_sym = index.symbols["core/engine.py::validate_card_limit"]
    assert "core/engine.py::PaymentProcessor.authorize" in val_sym.called_by
    assert "core/engine.py::async_settle" in val_sym.called_by


def test_find_enclosing_symbol_prefers_method_over_class():
    sources = {
        "svc/account.py": (
            "class Ledger:\n"
            "    def credit(self, cents: int) -> int:\n"
            "        if cents < 0:\n"
            "            raise ValueError('negative credit')\n"
            "        return cents\n"
        )
    }
    index = ASTSymbolIndex.from_sources(sources)
    sym = index.find_enclosing_symbol("svc/account.py", 4)
    assert sym is not None
    assert sym.qualified_name == "Ledger.credit"
    assert sym.kind == "method"


def test_fault_localizer_ranks_innermost_crashing_function_top1():
    sources = {
        "mathlib/stats.py": (
            "def normalize_weights(weights: list[float]) -> list[float]:\n"
            "    total = sum(weights)\n"
            "    return [w / total for w in weights]\n\n"
            "def weighted_average(values: list[float], weights: list[float]) -> float:\n"
            "    norm = normalize_weights(weights)\n"
            "    return sum(v * w for v, w in zip(values, norm))\n"
        ),
        "mathlib/report.py": (
            "from mathlib.stats import weighted_average\n\n"
            "def build_summary(values: list[float], weights: list[float]) -> float:\n"
            "    return weighted_average(values, weights)\n"
        ),
        "tests/test_stats.py": (
            "from mathlib.report import build_summary\n\n"
            "def test_zero_weights():\n"
            "    assert build_summary([1.0, 2.0], [0.0, 0.0]) == 0.0\n"
        ),
    }
    tb = (
        "Traceback (most recent call last):\n"
        '  File "tests/test_stats.py", line 4, in test_zero_weights\n'
        "    assert build_summary([1.0, 2.0], [0.0, 0.0]) == 0.0\n"
        '  File "mathlib/report.py", line 4, in build_summary\n'
        "    return weighted_average(values, weights)\n"
        '  File "mathlib/stats.py", line 6, in weighted_average\n'
        "    norm = normalize_weights(weights)\n"
        '  File "mathlib/stats.py", line 3, in normalize_weights\n'
        "    return [w / total for w in weights]\n"
        "ZeroDivisionError: float division by zero\n"
    )
    localizer = FaultLocalizer.from_sources(sources)
    res = localizer.localize(tb, top_k=3, token_budget=800)
    assert len(res.suspects) == 3
    assert res.suspects[0].symbol.symbol_id == "mathlib/stats.py::normalize_weights"
    assert res.suspects[1].symbol.symbol_id == "mathlib/stats.py::weighted_average"
    assert res.suspects[2].symbol.symbol_id == "mathlib/report.py::build_summary"


def test_fault_localizer_discovers_1hop_callee_when_assertion_fails_in_test():
    sources = {
        "pricing/discount.py": (
            "def compute_loyalty_rebate(points: int) -> int:\n"
            "    # Buggy rebate formula\n"
            "    return points // 50\n"
        ),
        "pricing/cart.py": (
            "from pricing.discount import compute_loyalty_rebate\n\n"
            "def checkout_total(subtotal: int, loyalty_points: int) -> int:\n"
            "    rebate = compute_loyalty_rebate(loyalty_points)\n"
            "    return subtotal - rebate\n"
        ),
        "tests/test_cart.py": (
            "from pricing.cart import checkout_total\n\n"
            "def test_loyalty_rebate_calculation():\n"
            "    assert checkout_total(100, 200) == 80\n"
        ),
    }
    tb = (
        "_______________________ test_loyalty_rebate_calculation _______________________\n\n"
        "tests/test_cart.py:4: in test_loyalty_rebate_calculation\n"
        "    assert checkout_total(100, 200) == 80\n"
        "E   AssertionError: assert 96 == 80\n"
        "E    +  where 96 = checkout_total(100, 200)\n"
    )
    localizer = FaultLocalizer.from_sources(sources)
    res = localizer.localize(tb, top_k=3, token_budget=800)
    ids = [s.symbol.symbol_id for s in res.suspects]
    assert "pricing/cart.py::checkout_total" in ids
    assert "pricing/discount.py::compute_loyalty_rebate" in ids


def test_fault_localizer_respects_strict_token_budget(tmp_path: Path):
    (tmp_path / "mod.py").write_text(
        "def alpha(x: int) -> int:\n"
        "    return beta(x) + 1\n\n"
        "def beta(x: int) -> int:\n"
        "    # Long docstring to consume tokens " + ("word " * 80) + "\n"
        "    return x * 2\n",
        encoding="utf-8",
    )
    tb = (
        '  File "mod.py", line 2, in alpha\n'
        "    return beta(x) + 1\n"
        '  File "mod.py", line 6, in beta\n'
        "    return x * 2\n"
        "ValueError: bad value\n"
    )
    localizer = FaultLocalizer.from_directory(tmp_path)
    res = localizer.localize(tb, top_k=5, token_budget=120)
    assert len(res.suspects) >= 1
    assert res.tokens_used <= 160
    prompt = res.format_context_prompt()
    assert "### Fault Localization Summary" in prompt
    assert "Suspect #1" in prompt

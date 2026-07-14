"""Language guardrails (strictly enforced) — through-function regression tests.

Methodology Language Guardrails: the standard disclaimer must appear in three
locations (report rendering, DealResult.limitations, DealResult.interpretation);
every breach flag carries the mechanical-test-result label; output never asserts
legal conclusions ("event of default", "acceleration available").
"""
from datetime import date

import pytest

from waterfall import run
from waterfall.data.schema import Deal, Tranche, CovenantConfig
from waterfall.report.schema import STANDARD_DISCLAIMER
from waterfall.report import export


def _distress_deal():
    senior = Tranche(name="Term A", tranche_type="senior", principal=10_000_000.0,
                     coupon=0.06, amort_type="bullet", term_periods=8)
    equity = Tranche(name="Equity", tranche_type="equity", principal=3_000_000.0)
    cfads = [900_000.0] * 8
    cfads[2] = 50_000.0          # forces a DSCR breach / cash-trap
    return Deal(
        deal_close_date=date(2024, 1, 1), operations_start_date=date(2024, 1, 1),
        period_frequency="Q", deal_type="PF", tranches=[senior, equity],
        cfads_stream=cfads, data_currency="USD", reporting_basis="calendar",
        covenants=[CovenantConfig(metric="DSCR", trap=1.10, default=1.00)],
    )


def test_disclaimer_present_in_three_locations():
    result = run(_distress_deal())
    # 1) limitations block carries the disclaimer via interpretation; 2) interpretation
    # string; 3) rendered report text.
    assert STANDARD_DISCLAIMER in result.interpretation
    assert any("input-preparer" in lim for lim in result.limitations)
    # L2: the disclaimer appears literally in DealResult.limitations (a named
    # methodology location), not only via interpretation.
    assert STANDARD_DISCLAIMER in result.limitations
    rendered = export.render_text(result)
    assert STANDARD_DISCLAIMER in rendered
    # The DealResult also exposes the disclaimer directly.
    assert result.disclaimer == STANDARD_DISCLAIMER


def test_breach_entries_carry_mechanical_test_label():
    result = run(_distress_deal())
    breaches = [r for r in result.audit_log if r.mechanical_test_result]
    assert breaches, "expected at least one mechanical-test-result breach entry"
    for r in breaches:
        assert "mechanical test result" in r.rationale


def test_no_legal_conclusion_strings_in_output():
    result = run(_distress_deal())
    rendered = export.render_text(result).lower()
    for banned in ("event of default", "acceleration available", "creditworthy",
                   "investable", "approvable"):
        assert banned not in rendered
    for r in result.audit_log:
        assert "event of default" not in r.rationale.lower()

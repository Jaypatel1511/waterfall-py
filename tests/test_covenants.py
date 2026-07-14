"""Covenant metrics (inline formulas) + three-tier cushion.

Methodology Covenant Pack: DSCR/LLCR/PLCR/LTV/debt-yield etc. defined inline;
division-by-zero -> n/a (NaN, never inf/0/raise); PLCR is PF-only; three-tier
cushion performance / trap / default.
"""
import math

import pytest

from waterfall.models import covenants
from waterfall.data.schema import CovenantConfig


def _isna(x):
    return isinstance(x, float) and math.isnan(x)


# --- DSCR -----------------------------------------------------------------
def test_dscr_senior_default_denominator():
    assert covenants.dscr(cfads=1_250_000, senior_ds=1_000_000) == pytest.approx(1.25)


def test_dscr_total_denominator_includes_mezz():
    v = covenants.dscr(cfads=1_200_000, senior_ds=1_000_000, mezz_ds=200_000,
                       denominator="total")
    assert v == pytest.approx(1.0)


def test_dscr_zero_debt_service_is_na_not_inf():
    v = covenants.dscr(cfads=500_000, senior_ds=0.0)
    assert _isna(v)          # never inf, 0, or raise


# --- LLCR / PLCR ----------------------------------------------------------
def test_llcr_pv_undiscounted():
    v = covenants.llcr(future_cfads=[100.0, 100.0, 100.0], senior_balance=200.0,
                       periodic_senior_cost=0.0)
    assert v == pytest.approx(1.5)


def test_llcr_pv_discounted():
    v = covenants.llcr(future_cfads=[100.0, 100.0], senior_balance=100.0,
                       periodic_senior_cost=0.10)
    expected = (100 / 1.1 + 100 / 1.1**2) / 100
    assert v == pytest.approx(expected)


def test_llcr_includes_dsra_when_configured():
    base = covenants.llcr([100.0], 100.0, 0.0)
    with_dsra = covenants.llcr([100.0], 100.0, 0.0, dsra=50.0, include_dsra=True)
    assert with_dsra == pytest.approx(base + 0.5)


def test_llcr_zero_balance_is_na():
    assert _isna(covenants.llcr([100.0], 0.0, 0.0))


def test_plcr_pf_only():
    pf = covenants.plcr([100.0, 100.0], 100.0, 0.0, deal_type="PF")
    assert pf == pytest.approx(2.0)
    cre = covenants.plcr([100.0, 100.0], 100.0, 0.0, deal_type="CRE")
    assert _isna(cre)        # CRE has no project life -> not computed


# --- LTV / debt yield / others -------------------------------------------
def test_ltv():
    assert covenants.ltv(debt_balance=7_000_000, asset_value=10_000_000) == pytest.approx(0.70)


def test_ltv_zero_asset_value_is_na():
    assert _isna(covenants.ltv(7_000_000, 0.0))


def test_debt_yield():
    assert covenants.debt_yield(noi=1_000_000, debt_balance=10_000_000) == pytest.approx(0.10)


def test_debt_yield_zero_balance_is_na():
    assert _isna(covenants.debt_yield(1_000_000, 0.0))


def test_interest_coverage_zero_interest_is_na():
    assert _isna(covenants.interest_coverage(cfads=1_000_000, interest=0.0))


# --- Three-tier cushion ---------------------------------------------------
def _cov(**over):
    base = dict(metric="DSCR", performance=1.20, trap=1.10, default=1.00)
    base.update(over)
    return CovenantConfig(**base)


@pytest.mark.parametrize("value,expected", [
    (1.30, "pass"),
    (1.15, "performance"),   # below minimum, above trap
    (1.05, "trap"),          # below trap, above default
    (0.90, "default"),       # below default
])
def test_coverage_metric_cushion_tiers(value, expected):
    assert covenants.evaluate(_cov(), value) == expected


def test_na_value_is_not_tested():
    assert covenants.evaluate(_cov(), float("nan")) == "n/a"


def test_leverage_metric_breaches_when_above_threshold():
    # LTV is "lower is better": breach when the ratio exceeds the threshold.
    cfg = CovenantConfig(metric="LTV", performance=0.70, trap=0.80, default=0.90)
    assert covenants.evaluate(cfg, 0.65) == "pass"
    assert covenants.evaluate(cfg, 0.75) == "performance"
    assert covenants.evaluate(cfg, 0.85) == "trap"
    assert covenants.evaluate(cfg, 0.95) == "default"


def test_unconfigured_tier_is_skipped():
    # Only a trap threshold configured; performance/default absent.
    cfg = CovenantConfig(metric="DSCR", trap=1.10)
    assert covenants.evaluate(cfg, 1.05) == "trap"
    assert covenants.evaluate(cfg, 1.50) == "pass"

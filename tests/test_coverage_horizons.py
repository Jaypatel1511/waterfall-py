"""LLCR vs PLCR horizons (audit H2; methodology Covenant Pack LOCKED).

LLCR present-values CFADS to *loan maturity*; PLCR to *end of project life*
(``project_life_periods``, PF-only). When maturity < project life the two metrics
must differ — the pre-fix engine handed both the identical full-remaining slice,
so they collapsed and ``project_life_periods`` was a dead field.

Deal: 5,000,000 senior bullet, loan maturity at period 4, project life 8 periods,
flat 1,000,000 CFADS, discount = 5% senior cost. Annual / 30/360.
"""
from datetime import date

import pytest

from waterfall import run
from waterfall.data.schema import Deal, Tranche, CovenantConfig
from waterfall.models import covenants as cov
from waterfall.data.exceptions import InvalidInputError

DC = "30/360"
_TD = dict(deal_close_date=date(2024, 1, 1), operations_start_date=date(2024, 1, 1),
           period_frequency="A", data_currency="USD", reporting_basis="calendar")


def _deal(covenants, project_life=8, deal_type="PF"):
    return Deal(**_TD, deal_type=deal_type, project_life_periods=project_life,
                tranches=[Tranche("Term A", "senior", 5_000_000.0, coupon=0.05,
                                  day_count=DC, amort_type="bullet", term_periods=4),
                          Tranche("Equity", "equity", 1_000_000.0)],
                cfads_stream=[1_000_000.0] * 8, covenants=covenants)


def test_llcr_and_plcr_use_distinct_horizons():
    # Hand PVs at t0 (discount 5%/period):
    #   LLCR horizon = loan maturity -> future = 3 periods -> PV/5M ~ 0.5446
    #   PLCR horizon = project life  -> future = 7 periods -> PV/5M ~ 1.1573
    expected_llcr = cov.pv([1_000_000.0] * 3, 0.05) / 5_000_000.0
    expected_plcr = cov.pv([1_000_000.0] * 7, 0.05) / 5_000_000.0
    assert expected_llcr == pytest.approx(0.5446, abs=1e-3)
    assert expected_plcr == pytest.approx(1.1573, abs=1e-3)

    r = run(_deal([CovenantConfig(metric="LLCR", performance=1.0),
                   CovenantConfig(metric="PLCR", performance=1.0)]))
    status0 = r.periods[0].covenant_status
    # LLCR (short horizon) breaches 1.0; PLCR (long horizon) passes -> distinct.
    assert status0["LLCR"] == "performance"
    assert status0["PLCR"] == "pass"


def test_llcr_value_is_bracketed_by_thresholds():
    # Brackets the LLCR magnitude (~0.5446) to prove the loan-maturity horizon.
    breach = run(_deal([CovenantConfig(metric="LLCR", performance=0.55)]))
    ok = run(_deal([CovenantConfig(metric="LLCR", performance=0.54)]))
    assert breach.periods[0].covenant_status["LLCR"] == "performance"  # 0.5446 < 0.55
    assert ok.periods[0].covenant_status["LLCR"] == "pass"             # 0.5446 > 0.54


def test_plcr_value_is_bracketed_by_thresholds():
    # Brackets the PLCR magnitude (~1.1573) to prove the project-life horizon.
    breach = run(_deal([CovenantConfig(metric="PLCR", performance=1.16)]))
    ok = run(_deal([CovenantConfig(metric="PLCR", performance=1.15)]))
    assert breach.periods[0].covenant_status["PLCR"] == "performance"  # 1.1573 < 1.16
    assert ok.periods[0].covenant_status["PLCR"] == "pass"             # 1.1573 > 1.15


def test_pf_plcr_requires_project_life_periods():
    with pytest.raises(InvalidInputError):
        _deal([CovenantConfig(metric="PLCR", performance=1.0)], project_life=None)


def test_cre_reports_plcr_as_na_without_project_life():
    # CRE has no project life; PLCR is n/a and project_life_periods is not required.
    r = run(_deal([CovenantConfig(metric="PLCR", performance=1.0)],
                  project_life=None, deal_type="CRE"))
    assert r.periods[0].covenant_status["PLCR"] == "n/a"

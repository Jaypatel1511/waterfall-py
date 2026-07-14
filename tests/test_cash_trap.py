"""Cash-trap / lock-up behavior — the C1 fix and the M2 no-leak guarantee.

Methodology "Cash-trap / lock-up behavior" (LOCKED): a trap forces the step-5 ECF
sweep to 100%; while the trap is active AND debt remains outstanding, steps 6-7
receive no cash (no distribution leaks to equity). **Edge (C1):** if the forced
100% sweep fully retires ALL debt in a period, the trap is moot and the residual
operating cash flows to step-7 equity — no stranded cash, cash-conservation holds.

Annual periods, 30/360 -> interest is exactly coupon x balance.
"""
from datetime import date

import pytest

from waterfall import run
from waterfall.data.schema import Deal, Tranche, CovenantConfig

DC = "30/360"
_TD = dict(deal_close_date=date(2024, 1, 1), operations_start_date=date(2024, 1, 1),
           period_frequency="A", data_currency="USD", reporting_basis="calendar")
_EQUITY = Tranche("Equity", "equity", 1_000_000.0)


def _cash_conservation_holds(result):
    for led in result.ledgers:
        assert led.total_sources() == pytest.approx(led.total_uses(), abs=1e-6)


# ==========================================================================
# C1 — a trap whose forced 100% sweep retires ALL debt -> residual to equity.
# Senior 1.5M bullet; CFADS high early then collapses, so LLCR (PV of future
# CFADS / senior balance) breaches the trap at t2 while current CFADS is still
# 2,000,000 — the exact shape the audit flagged.
# ==========================================================================
def _c1_deal(deal_type="PF"):
    return Deal(**_TD, deal_type=deal_type,
                tranches=[Tranche("Term A", "senior", 1_500_000.0, coupon=0.05,
                                  day_count=DC, amort_type="bullet", term_periods=5),
                          _EQUITY],
                cfads_stream=[2_000_000.0, 2_000_000.0, 2_000_000.0, 100_000.0, 100_000.0],
                covenants=[CovenantConfig(metric="LLCR", trap=1.0)])


def test_c1_trap_retires_all_debt_routes_residual_to_equity():
    # Regression: this deal raised WaterfallImbalanceError pre-fix (residual stranded).
    r = run(_c1_deal())          # must not raise
    _cash_conservation_holds(r)

    p2 = r.periods[2]
    assert p2.covenant_status["LLCR"] == "trap"          # trap active this period
    # Forced 100% sweep retires the whole 1,500,000 senior balance...
    assert p2.sweep_amount == pytest.approx(1_500_000.0)
    assert p2.principal_by_tranche["Term A"] == pytest.approx(1_500_000.0)
    # ...and the leftover (2,000,000 - 75,000 interest - 1,500,000) flows to equity.
    assert p2.equity_distribution == pytest.approx(425_000.0)
    # Debt is fully retired at end of period 2.
    ending = {row["tranche"]: row["ending_balance"] for row in r.tranche_summary}
    assert ending["Term A"] == pytest.approx(0.0)


# ==========================================================================
# M2 — while a trap is active AND debt remains, no cash leaks to equity and the
# sweep is forced to 100% of ECF. Senior 5M bullet, flat 2M CFADS: LLCR breaches
# the trap at t2 and t3, and 5M cannot be retired by a single-period sweep.
# ==========================================================================
def _m2_deal():
    return Deal(**_TD, deal_type="PF",
                tranches=[Tranche("Term A", "senior", 5_000_000.0, coupon=0.05,
                                  day_count=DC, amort_type="bullet", term_periods=5),
                          _EQUITY],
                cfads_stream=[2_000_000.0] * 5,
                covenants=[CovenantConfig(metric="LLCR", trap=1.0)])


def test_trap_forces_full_sweep_and_no_leak_while_debt_remains():
    r = run(_m2_deal())
    _cash_conservation_holds(r)

    p2 = r.periods[2]
    assert p2.covenant_status["LLCR"] == "trap"
    # ECF = 2,000,000 - 250,000 interest = 1,750,000, swept at the forced 100%.
    assert p2.sweep_amount == pytest.approx(1_750_000.0)
    # Debt still outstanding -> steps 6-7 gated -> nothing to equity.
    assert p2.equity_distribution == pytest.approx(0.0)
    ending = {row["tranche"]: row["ending_balance"] for row in r.tranche_summary}
    # (senior still outstanding right after t2: 5,000,000 - 1,750,000 = 3,250,000)
    assert r.periods[3].covenant_status["LLCR"] == "trap"
    assert r.periods[3].equity_distribution == pytest.approx(0.0)

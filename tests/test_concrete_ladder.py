"""Concrete per-step dollar pins for the ladder (audit H4).

The pre-fix integration suite only checked "runs + cash-conservation identity +
CFADS purity", and the identity ties out for ANY allocation of cash across steps
— so it could not catch a mis-allocation *inside* the ladder. These tests pin the
exact per-step figures (senior/mezz interest & principal, sweep, reserve
movements, step-6 6a/6b/6c, distribution, DSCR magnitude) for hand-computable
deals, so a mutation that moves money to the wrong step/tranche fails a test.

All deals use annual periods with 30/360 day-count, so the day-count fraction is
exactly 1.0 and every interest figure is coupon x balance. Ladder mechanics are
deal-type-independent here (no LLCR/PLCR), so each deal is run for both PF and CRE
and must produce identical figures.
"""
from datetime import date

import pytest

from waterfall import run
from waterfall.data.schema import Deal, Tranche, ReserveConfig, CovenantConfig

DC = "30/360"
_TD = dict(deal_close_date=date(2024, 1, 1), operations_start_date=date(2024, 1, 1),
           period_frequency="A", data_currency="USD", reporting_basis="calendar")
DEAL_TYPES = ["PF", "CRE"]


def _senior(**over):
    return Tranche("Term A", "senior", 10_000_000.0, coupon=0.05, day_count=DC,
                   amort_type="fully_amortizing", term_periods=4, **over)


def _mezz(**over):
    return Tranche("Mezz", "mezzanine", 2_000_000.0, coupon=0.10, day_count=DC,
                   amort_type="bullet", term_periods=4, **over)


_EQUITY = Tranche("Equity", "equity", 1_000_000.0)


def _ledger_use(result, period, label):
    """Sum of a labeled ledger USE in one period (0 if absent)."""
    from waterfall.audit.log import USE
    led = result.ledgers[period]
    return sum(e.amount for e in led.entries if e.kind == USE and e.label == label)


def _cash_conservation_holds(result):
    for led in result.ledgers:
        assert led.total_sources() == pytest.approx(led.total_uses(), abs=1e-6)


# ==========================================================================
# Deal A — surplus, no sweep: pins steps 1/2/4/6c + DSCR denominator (senior)
# ==========================================================================
def _deal_A(deal_type):
    return Deal(**_TD, deal_type=deal_type,
                tranches=[_senior(), _mezz(), _EQUITY],
                cfads_stream=[5_000_000.0] * 4,
                covenants=[CovenantConfig(metric="DSCR", performance=1.20)])


@pytest.mark.parametrize("deal_type", DEAL_TYPES)
def test_surplus_ladder_concrete(deal_type):
    r = run(_deal_A(deal_type))
    _cash_conservation_holds(r)

    p0 = r.periods[0]
    # Step 2 — senior: interest 0.05 x 10,000,000 x 1.0 = 500,000; scheduled 2,500,000.
    assert p0.interest_by_tranche["Term A"] == pytest.approx(500_000.0)
    assert p0.principal_by_tranche["Term A"] == pytest.approx(2_500_000.0)
    # Step 4 — mezz: interest 0.10 x 2,000,000 = 200,000; bullet -> no principal.
    assert p0.interest_by_tranche["Mezz"] == pytest.approx(200_000.0)
    assert p0.principal_by_tranche["Mezz"] == pytest.approx(0.0)
    # Step 5 — no sweep configured, no trap -> zero swept.
    assert p0.sweep_amount == pytest.approx(0.0)
    # Steps 6/7 — retained cash to distribution: 5,000,000 - 3,000,000 - 200,000.
    assert p0.equity_distribution == pytest.approx(1_800_000.0)
    assert p0.junior_uses["reserve_topups"] == pytest.approx(0.0)
    # DSCR denominator is SENIOR debt service (3,000,000), NOT total (3,200,000).
    assert p0.dscr == pytest.approx(5_000_000.0 / 3_000_000.0)
    assert p0.dscr != pytest.approx(5_000_000.0 / 3_200_000.0)

    # Final period: senior balance 2,500,000 -> interest 125,000; mezz bullet repays.
    p3 = r.periods[3]
    assert p3.interest_by_tranche["Term A"] == pytest.approx(125_000.0)
    assert p3.principal_by_tranche["Term A"] == pytest.approx(2_500_000.0)
    assert p3.principal_by_tranche["Mezz"] == pytest.approx(2_000_000.0)
    assert p3.equity_distribution == pytest.approx(175_000.0)
    assert p3.dscr == pytest.approx(5_000_000.0 / 2_625_000.0)


# ==========================================================================
# Deal B — DSRA draw then step-3 replenishment (kills M18)
# ==========================================================================
def _deal_B(deal_type):
    return Deal(**_TD, deal_type=deal_type,
                tranches=[_senior(), _mezz(), _EQUITY],
                cfads_stream=[5_000_000.0, 2_800_000.0, 5_000_000.0, 5_000_000.0],
                reserves=[ReserveConfig(reserve_type="DSRA", required=True,
                                        target_amount=600_000.0,
                                        opening_balance=600_000.0)],
                covenants=[CovenantConfig(metric="DSCR", performance=1.20)])


@pytest.mark.parametrize("deal_type", DEAL_TYPES)
def test_dsra_draw_then_step3_replenish_concrete(deal_type):
    r = run(_deal_B(deal_type))
    _cash_conservation_holds(r)

    # t1: senior DS = 375,000 int + 2,500,000 sched = 2,875,000; CFADS 2,800,000
    # -> 75,000 shortfall drawn from the DSRA (600,000 -> 525,000). No distribution.
    p1 = r.periods[1]
    assert p1.reserve_draws == pytest.approx(75_000.0)
    assert p1.reserve_balances["DSRA"] == pytest.approx(525_000.0)
    assert p1.equity_distribution == pytest.approx(0.0)

    # t2: step-3 required replenishment funds the DSRA back to 600,000 (75,000).
    p2 = r.periods[2]
    assert _ledger_use(r, 2, "reserve_funding") == pytest.approx(75_000.0)
    assert p2.reserve_balances["DSRA"] == pytest.approx(600_000.0)


# ==========================================================================
# Deal F — step-6b discretionary reserve top-up (kills M1)
# ==========================================================================
def _deal_F(deal_type):
    return Deal(**_TD, deal_type=deal_type,
                tranches=[_senior(), _mezz(), _EQUITY],
                cfads_stream=[5_000_000.0] * 4,
                reserves=[ReserveConfig(reserve_type="capex", required=False,
                                        opening_balance=100_000.0,
                                        discretionary_target=250_000.0,
                                        topup_cap_per_period=90_000.0)],
                covenants=[CovenantConfig(metric="DSCR", performance=1.20)])


@pytest.mark.parametrize("deal_type", DEAL_TYPES)
def test_step6b_discretionary_topup_concrete(deal_type):
    r = run(_deal_F(deal_type))
    _cash_conservation_holds(r)

    # t0: retained cash 1,800,000; step-6b tops up capex by the 90,000 cap
    # (100,000 -> 190,000); step-6c distribution is the remaining 1,710,000.
    p0 = r.periods[0]
    assert p0.junior_uses["reserve_topups"] == pytest.approx(90_000.0)
    assert p0.reserve_balances["capex"] == pytest.approx(190_000.0)
    assert p0.equity_distribution == pytest.approx(1_710_000.0)
    assert _ledger_use(r, 0, "reserve_topup") == pytest.approx(90_000.0)

    # t1: only 60,000 of room remains to the 250,000 target (under the 90,000 cap).
    p1 = r.periods[1]
    assert p1.junior_uses["reserve_topups"] == pytest.approx(60_000.0)
    assert p1.reserve_balances["capex"] == pytest.approx(250_000.0)
    assert p1.equity_distribution == pytest.approx(1_865_000.0)

    # t2: at target -> no further top-up, full retained cash distributed.
    p2 = r.periods[2]
    assert p2.junior_uses["reserve_topups"] == pytest.approx(0.0)
    assert p2.equity_distribution == pytest.approx(2_050_000.0)

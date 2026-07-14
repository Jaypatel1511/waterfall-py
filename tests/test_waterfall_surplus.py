"""Integration: a surplus period runs, ties out, and behaves mechanically.

This is the first end-to-end test of the ladder engine. It exercises the happy
path (CFADS comfortably covers debt service) and asserts the period
cash-conservation identity balances for every period without spurious raises.
"""
from datetime import date

import pytest

from waterfall import run
from waterfall.data.schema import Deal, Tranche, ReserveConfig, SweepConfig, SweepBand


def _surplus_pf_deal():
    senior = Tranche(name="Term A", tranche_type="senior", principal=10_000_000.0,
                     coupon=0.06, day_count="ACT/360", amort_type="bullet",
                     term_periods=8)
    mezz = Tranche(name="Mezz", tranche_type="mezzanine", principal=2_000_000.0,
                   coupon=0.10, amort_type="bullet", term_periods=8)
    equity = Tranche(name="Sponsor Equity", tranche_type="equity", principal=3_000_000.0)
    return Deal(
        deal_close_date=date(2024, 1, 1),
        operations_start_date=date(2024, 1, 1),
        period_frequency="Q",
        deal_type="PF",
        tranches=[senior, mezz, equity],
        cfads_stream=[900_000.0] * 8,     # comfortably above quarterly debt service
        data_currency="USD",
        reporting_basis="calendar",
        reserves=[ReserveConfig(reserve_type="DSRA", months_dsra=6,
                                opening_balance=750_000.0)],
        sweep=SweepConfig(bands=[SweepBand(10.0, 0.5)], default_sweep_pct=0.5),
    )


def test_run_returns_one_result_per_period():
    result = run(_surplus_pf_deal())
    assert len(result.periods) == 8


def test_cash_conservation_holds_every_period():
    result = run(_surplus_pf_deal())
    for led in result.ledgers:
        assert led.total_sources() == pytest.approx(led.total_uses(), abs=1e-6)


def test_senior_interest_is_paid_in_surplus():
    result = run(_surplus_pf_deal())
    assert result.periods[0].interest_by_tranche["Term A"] > 0


def test_cfads_stays_operating_only():
    # The reported CFADS must equal the user input — reserves/draws never folded in.
    deal = _surplus_pf_deal()
    result = run(deal)
    for p, raw in zip(result.periods, deal.cfads_stream):
        assert p.cfads == pytest.approx(raw)


def test_equity_distribution_nonnegative_and_only_in_surplus():
    result = run(_surplus_pf_deal())
    assert all(p.equity_distribution >= -1e-9 for p in result.periods)


def test_dscr_reported_per_period():
    result = run(_surplus_pf_deal())
    # DSCR = CFADS / senior debt service; comfortably above 1.0 here.
    assert result.periods[0].dscr > 1.0

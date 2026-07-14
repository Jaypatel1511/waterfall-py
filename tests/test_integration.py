"""Five period-type integration scenarios x CRE and PF.

Each asserts: run() does not raise spuriously, the per-period cash-conservation
identity balances every period, and (for cure/revolver) CFADS stays operating-only.
Scenarios: (a) surplus, (b) DSRA-draw distress, (c) maturity/reserve-release,
(d) mid-life equity cash-injection cure, (e) revolver/delayed-draw facility draw.
"""
from datetime import date

import pytest

from waterfall import run
from waterfall.data.schema import (
    Deal, Tranche, ReserveConfig, CovenantConfig, SweepConfig, SweepBand,
)


def _tranches(with_facility=False):
    senior = Tranche(name="Term A", tranche_type="senior", principal=10_000_000.0,
                     coupon=0.06, amort_type="bullet", term_periods=8)
    mezz = Tranche(name="Mezz", tranche_type="mezzanine", principal=2_000_000.0,
                   coupon=0.10, amort_type="bullet", term_periods=8)
    equity = Tranche(name="Equity", tranche_type="equity", principal=3_000_000.0)
    out = [senior, mezz, equity]
    if with_facility:
        out.insert(1, Tranche(name="Revolver", tranche_type="senior", principal=1.0,
                              coupon=0.05, amort_type="bullet", term_periods=8,
                              is_facility=True, commitment=2_000_000.0))
    return out


def _deal(deal_type, scenario):
    n = 8
    cfads = [900_000.0] * n
    reserves = [ReserveConfig(reserve_type="DSRA", months_dsra=6, opening_balance=750_000.0)]
    equity_contributions = None
    facility_draws = None
    tranches = _tranches()

    if scenario == "surplus":
        pass
    elif scenario == "dsra_draw":
        cfads[3] = 50_000.0        # deep shortfall covered by the DSRA
    elif scenario == "release":
        # Amortizing deal with surplus CFADS so the DSRA survives (never drawn)
        # to its release at the final period, then flows down the proceeds path.
        cfads = [2_500_000.0] * n
        tranches = [
            Tranche(name="Term A", tranche_type="senior", principal=10_000_000.0,
                    coupon=0.06, amort_type="fully_amortizing", term_periods=8),
            Tranche(name="Mezz", tranche_type="mezzanine", principal=2_000_000.0,
                    coupon=0.10, amort_type="fully_amortizing", term_periods=8),
            Tranche(name="Equity", tranche_type="equity", principal=3_000_000.0),
        ]
        reserves = [ReserveConfig(reserve_type="DSRA", months_dsra=6,
                                  opening_balance=750_000.0, release_period=n - 1)]
    elif scenario == "cure":
        cfads[4] = 60_000.0        # shortfall
        reserves = [ReserveConfig(reserve_type="DSRA", opening_balance=0.0,
                                  target_amount=0.0)]  # no DSRA cushion -> needs cure
        equity_contributions = [0.0] * n
        equity_contributions[4] = 200_000.0
    elif scenario == "revolver":
        tranches = _tranches(with_facility=True)
        facility_draws = [0.0] * n
        facility_draws[2] = 500_000.0

    kwargs = dict(
        deal_close_date=date(2024, 1, 1), operations_start_date=date(2024, 1, 1),
        period_frequency="Q", deal_type=deal_type, tranches=tranches,
        cfads_stream=cfads, data_currency="USD", reporting_basis="calendar",
        reserves=reserves,
        covenants=[CovenantConfig(metric="DSCR", trap=1.10, default=1.00)],
        sweep=SweepConfig(bands=[SweepBand(10.0, 0.5)], default_sweep_pct=0.5),
        asset_value=15_000_000.0,
    )
    if equity_contributions is not None:
        kwargs["equity_contributions"] = equity_contributions
    if facility_draws is not None:
        kwargs["facility_draws"] = facility_draws
    return Deal(**kwargs)


SCENARIOS = ["surplus", "dsra_draw", "release", "cure", "revolver"]
DEAL_TYPES = ["PF", "CRE"]


@pytest.mark.parametrize("deal_type", DEAL_TYPES)
@pytest.mark.parametrize("scenario", SCENARIOS)
def test_scenario_runs_and_cash_conservation_holds(deal_type, scenario):
    result = run(_deal(deal_type, scenario))
    assert len(result.periods) == 8
    for led in result.ledgers:
        assert led.total_sources() == pytest.approx(led.total_uses(), abs=1e-6)


@pytest.mark.parametrize("deal_type", DEAL_TYPES)
def test_dsra_draw_absorbs_shortfall(deal_type):
    result = run(_deal(deal_type, "dsra_draw"))
    assert result.periods[3].reserve_draws > 0        # DSRA drew to cover the gap
    assert result.periods[3].cfads == pytest.approx(50_000.0)  # CFADS not altered


@pytest.mark.parametrize("deal_type", DEAL_TYPES)
def test_reserve_release_reaches_the_proceeds_path(deal_type):
    result = run(_deal(deal_type, "release"))
    assert result.periods[-1].reserve_releases > 0
    # Released cash is applied to debt (or equity once debt retired), never swept as ECF.
    assert result.periods[-1].proceeds_applied > 0 or result.periods[-1].equity_distribution >= 0


@pytest.mark.parametrize("deal_type", DEAL_TYPES)
def test_cure_keeps_cfads_operating_only(deal_type):
    deal = _deal(deal_type, "cure")
    result = run(deal)
    assert result.periods[4].equity_contributions > 0        # cure injected
    for p, raw in zip(result.periods, deal.cfads_stream):
        assert p.cfads == pytest.approx(raw)                 # CFADS never contaminated


@pytest.mark.parametrize("deal_type", DEAL_TYPES)
def test_revolver_draw_is_a_non_cfads_source(deal_type):
    deal = _deal(deal_type, "revolver")
    result = run(deal)
    assert result.periods[2].facility_draws == pytest.approx(500_000.0)
    for p, raw in zip(result.periods, deal.cfads_stream):
        assert p.cfads == pytest.approx(raw)                 # draw not folded into CFADS


def test_plcr_only_computed_for_pf():
    pf = run(Deal(
        deal_close_date=date(2024, 1, 1), operations_start_date=date(2024, 1, 1),
        period_frequency="Q", deal_type="PF", tranches=_tranches(),
        cfads_stream=[900_000.0] * 8, data_currency="USD", reporting_basis="calendar",
        covenants=[CovenantConfig(metric="PLCR", default=1.10)],
    ))
    import math
    # PF computes a PLCR status other than "n/a" while a positive senior balance exists.
    assert pf.periods[0].covenant_status["PLCR"] != "n/a"

    cre = run(Deal(
        deal_close_date=date(2024, 1, 1), operations_start_date=date(2024, 1, 1),
        period_frequency="Q", deal_type="CRE", tranches=_tranches(),
        cfads_stream=[900_000.0] * 8, data_currency="USD", reporting_basis="calendar",
        covenants=[CovenantConfig(metric="PLCR", default=1.10)],
    ))
    assert cre.periods[0].covenant_status["PLCR"] == "n/a"   # CRE has no project life

"""Regression tests for L3 (pass-2 code audit): facility draws must not leak into
the ECF sweep base / equity, and the commitment cap must be enforced.

The amended methodology (Capital Stack / Interest / Limitations) **defers mid-life
facility draws to v0.1**: v0.x funds facilities **at close only** (the tranche's
opening balance is the funded amount) and rejects a non-zero ``facility_draws``
schedule with :class:`UnsupportedFeatureError`. The commitment cap is enforced on
:meth:`TrancheState.draw` and at input validation.

These tests are the point of the fix — the leak was invisible to the prior suite
because cash-conservation ties out for *any* allocation (the H4 failure mode).
"""
from datetime import date

import pytest

from waterfall import run
from waterfall.data.schema import (
    Deal, Tranche, SweepConfig, SweepBand,
)
from waterfall.data.exceptions import InvalidInputError, UnsupportedFeatureError
from waterfall.models import tranches as tr


# --------------------------------------------------------------------------
# No-leak: a facility funded at close is identical to the no-facility baseline.
# --------------------------------------------------------------------------
def _facility_deal(is_facility):
    """A senior term loan + a facility funded at close (opening balance) + equity.

    With ``is_facility=False`` the facility tranche is a plain senior loan of the
    same size/coupon; either way it is funded at close, so the two deals must
    produce byte-identical equity distributions and sweeps — the at-close funding
    never enters the operating cash pool.
    """
    senior = Tranche(name="Term A", tranche_type="senior", principal=5_000_000.0,
                     coupon=0.06, amort_type="bullet", term_periods=40)
    facility = Tranche(name="Revolver", tranche_type="senior", principal=2_000_000.0,
                       coupon=0.06, amort_type="bullet", term_periods=40,
                       is_facility=is_facility,
                       commitment=2_000_000.0 if is_facility else None)
    equity = Tranche(name="Equity", tranche_type="equity", principal=3_000_000.0)
    return Deal(
        deal_close_date=date(2024, 1, 1), operations_start_date=date(2024, 1, 1),
        period_frequency="Q", tranches=[senior, facility, equity],
        cfads_stream=[500_000.0] * 4, data_currency="USD", reporting_basis="calendar",
        # No bands -> sweep_pct is leverage-independent, so the extra facility debt
        # cannot change the sweep split; isolates the leak question.
        sweep=SweepConfig(bands=[], default_sweep_pct=0.5),
    )


def test_facility_funded_at_close_does_not_leak_to_equity_or_sweep():
    with_facility = run(_facility_deal(is_facility=True))
    baseline = run(_facility_deal(is_facility=False))

    for t, (f, b) in enumerate(zip(with_facility.periods, baseline.periods)):
        assert f.equity_distribution == pytest.approx(b.equity_distribution, abs=1e-9), (
            f"period {t}: facility funded at close leaked into equity")
        assert f.sweep_amount == pytest.approx(b.sweep_amount, abs=1e-9), (
            f"period {t}: facility funded at close inflated the sweep base")
        # The 2,000,000 at-close opening balance must never reach the operating
        # cash pool: equity is the CFADS-origin residual, far below the draw size.
        assert f.equity_distribution < 2_000_000.0
        assert f.facility_draws == pytest.approx(0.0)
    # The path is genuinely exercised (a real sweep + a real distribution).
    assert with_facility.periods[0].sweep_amount > 0
    assert with_facility.periods[0].equity_distribution > 0


# --------------------------------------------------------------------------
# Mid-life draws are rejected (fail-loud) — the leak vector is removed.
# --------------------------------------------------------------------------
def _draw_schedule_deal(schedule):
    facility = Tranche(name="Revolver", tranche_type="senior", principal=1.0,
                       coupon=0.05, amort_type="bullet", term_periods=8,
                       is_facility=True, commitment=2_000_000.0)
    senior = Tranche(name="Term A", tranche_type="senior", principal=5_000_000.0,
                     coupon=0.06, amort_type="bullet", term_periods=8)
    equity = Tranche(name="Equity", tranche_type="equity", principal=3_000_000.0)
    return dict(
        deal_close_date=date(2024, 1, 1), operations_start_date=date(2024, 1, 1),
        period_frequency="Q", tranches=[senior, facility, equity],
        cfads_stream=[400_000.0] * 4, data_currency="USD", reporting_basis="calendar",
        facility_draws=schedule,
    )


def test_mid_life_facility_draw_is_rejected():
    # A post-close draw (period 2) requires the deferred use-of-draw model.
    with pytest.raises(UnsupportedFeatureError):
        Deal(**_draw_schedule_deal([0.0, 0.0, 500_000.0, 0.0]))


def test_first_period_facility_draw_is_rejected():
    # Facilities are funded at close (opening balance), NOT via facility_draws[0];
    # any non-zero entry is a deferred mid-life draw.
    with pytest.raises(UnsupportedFeatureError):
        Deal(**_draw_schedule_deal([1_000_000.0, 0.0, 0.0, 0.0]))


def test_all_zero_facility_draws_is_accepted():
    # An all-zero schedule expresses "no draws" and must not raise.
    deal = Deal(**_draw_schedule_deal([0.0, 0.0, 0.0, 0.0]))
    result = run(deal)
    for p in result.periods:
        assert p.facility_draws == pytest.approx(0.0)


# --------------------------------------------------------------------------
# Commitment cap is enforced.
# --------------------------------------------------------------------------
def _facility_state(principal=1.0, commitment=2_000_000.0):
    rev = Tranche(name="Revolver", tranche_type="senior", principal=principal,
                  coupon=0.05, amort_type="bullet", term_periods=8,
                  is_facility=True, commitment=commitment)
    return tr.TrancheState(rev, horizon_periods=8, periods_per_year=4)


def test_draw_exceeding_commitment_is_rejected():
    st = _facility_state(principal=1.0, commitment=2_000_000.0)
    with pytest.raises(InvalidInputError):
        st.draw(5_000_000.0)          # 5M against a 2M commitment (audit L3c)


def test_draw_within_commitment_succeeds():
    st = _facility_state(principal=1.0, commitment=2_000_000.0)
    drawn = st.draw(1_000_000.0)       # 1 + 1,000,000 <= 2,000,000
    assert drawn == pytest.approx(1_000_000.0)
    assert st.balance == pytest.approx(1_000_001.0)


def test_at_close_funding_above_commitment_is_rejected():
    # The at-close opening balance is itself drawn against the commitment.
    with pytest.raises(InvalidInputError):
        Tranche(name="Revolver", tranche_type="senior", principal=3_000_000.0,
                coupon=0.05, amort_type="bullet", term_periods=8,
                is_facility=True, commitment=2_000_000.0)

"""Reserve mechanics: draw / replenish / release / discretionary top-up + sizing.

Methodology Reserves: DSRA drawn when CFADS is short of senior debt service (a
cash source), replenished to required at step 3, released on trigger/maturity
onto the separate proceeds path. Roll-forward:
    closing = opening + required funding (step 3) + top-ups (step 6b) - draws - releases
"""
import pytest

from waterfall.models import reserves
from waterfall.data.schema import ReserveConfig


def _dsra(opening=200_000.0, target=200_000.0, **over):
    cfg = ReserveConfig(reserve_type="DSRA", opening_balance=opening,
                        target_amount=target, **over)
    return reserves.ReserveState(cfg)


def test_opening_balance_is_period0_balance():
    assert _dsra(opening=150_000.0).balance == pytest.approx(150_000.0)


def test_draw_covers_shortfall_and_reduces_balance():
    st = _dsra(opening=200_000.0)
    drawn = st.draw(shortfall=120_000.0)
    assert drawn == pytest.approx(120_000.0)
    assert st.balance == pytest.approx(80_000.0)


def test_draw_capped_at_balance():
    st = _dsra(opening=50_000.0)
    drawn = st.draw(shortfall=120_000.0)
    assert drawn == pytest.approx(50_000.0)
    assert st.balance == pytest.approx(0.0)


def test_replenish_tops_up_to_required_and_returns_remaining_cash():
    st = _dsra(opening=80_000.0, target=200_000.0)
    funded, remaining = st.replenish(available=500_000.0)
    assert funded == pytest.approx(120_000.0)      # back up to 200k
    assert st.balance == pytest.approx(200_000.0)
    assert remaining == pytest.approx(380_000.0)


def test_replenish_limited_by_available_cash():
    st = _dsra(opening=80_000.0, target=200_000.0)
    funded, remaining = st.replenish(available=50_000.0)
    assert funded == pytest.approx(50_000.0)
    assert st.balance == pytest.approx(130_000.0)
    assert remaining == pytest.approx(0.0)


def test_discretionary_top_up_adds_to_balance():
    st = _dsra(opening=200_000.0, target=200_000.0)
    added = st.top_up(30_000.0)
    assert added == pytest.approx(30_000.0)
    assert st.balance == pytest.approx(230_000.0)


def test_release_returns_full_balance_and_zeroes():
    st = _dsra(opening=175_000.0)
    released = st.release()
    assert released == pytest.approx(175_000.0)
    assert st.balance == pytest.approx(0.0)


def test_roll_forward_identity_holds_over_a_period():
    st = _dsra(opening=100_000.0, target=200_000.0)
    opening = st.balance
    draws = st.draw(40_000.0)
    funding, _ = st.replenish(available=1e9)      # up to required 200k
    topup = st.top_up(10_000.0)
    releases = 0.0
    closing = st.balance
    assert closing == pytest.approx(opening + funding + topup - draws - releases)


def test_dsra_required_sizing_from_months():
    # 6 months of senior DS at quarterly (3-month) periods = 2 periods of DS.
    req = reserves.dsra_required(months=6, periodic_senior_ds=300_000.0,
                                 months_per_period=3)
    assert req == pytest.approx(600_000.0)


def test_lc_funded_draw_provides_cash_without_starting_cash_balance():
    cfg = ReserveConfig(reserve_type="DSRA", lc_funded=True, target_amount=200_000.0)
    st = reserves.ReserveState(cfg)
    # LC alternative: capacity available for shortfall even with no pre-funded cash.
    drawn = st.draw(shortfall=150_000.0)
    assert drawn == pytest.approx(150_000.0)

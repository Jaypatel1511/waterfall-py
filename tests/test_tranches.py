import pytest
from waterfall.data.schema import Tranche
from waterfall.models.tranches import build_states, TrancheState


def test_annual_interest(senior_tranche):
    assert senior_tranche.annual_interest == pytest.approx(7_000_000 * 0.06)


def test_scheduled_principal(senior_tranche):
    assert senior_tranche.scheduled_annual_principal == pytest.approx(700_000)


def test_equity_no_principal(equity_tranche):
    assert equity_tranche.scheduled_annual_principal == 0.0


def test_build_states(senior_tranche, mezz_tranche):
    states = build_states([senior_tranche, mezz_tranche])
    assert len(states) == 2
    assert states[0].outstanding_balance == 7_000_000
    assert states[1].outstanding_balance == 2_000_000


def test_pay_interest_full(senior_tranche):
    states = build_states([senior_tranche])
    state = states[0]
    paid, remaining, shortfall = state.pay_interest(1_000_000)
    assert paid == pytest.approx(7_000_000 * 0.06)
    assert shortfall == pytest.approx(0.0)


def test_pay_interest_partial(senior_tranche):
    states = build_states([senior_tranche])
    state = states[0]
    paid, remaining, shortfall = state.pay_interest(100)
    assert paid == pytest.approx(100)
    assert shortfall > 0


def test_pay_principal_reduces_balance(senior_tranche):
    states = build_states([senior_tranche])
    state = states[0]
    paid, remaining, shortfall = state.pay_principal(1_000_000)
    assert state.outstanding_balance == pytest.approx(7_000_000 - 700_000)


def test_sweep_reduces_balance(senior_tranche):
    states = build_states([senior_tranche])
    state = states[0]
    swept, remaining = state.sweep(500_000, pct=1.0)
    assert swept == pytest.approx(500_000)
    assert state.outstanding_balance == pytest.approx(6_500_000)


def test_invalid_tranche_raises():
    with pytest.raises(ValueError):
        Tranche(name="Bad", principal=-1, rate=0.05, term_years=5, priority=1)

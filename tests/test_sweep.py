import pytest
from waterfall.models.tranches import build_states
from waterfall.models.sweep import apply


def test_sweep_reduces_senior_balance(senior_tranche):
    states = build_states([senior_tranche])
    result = apply(
        period=1,
        available_cash=500_000,
        senior_states=states,
        mezz_states=[],
        cash_sweep_pct=1.0,
        dscr_lock_up=False,
    )
    assert result.swept_to_senior == pytest.approx(500_000)
    assert result.equity_distribution == pytest.approx(0.0)


def test_equity_distribution_when_unlocked(senior_tranche):
    states = build_states([senior_tranche])
    # Pay off the senior tranche first
    states[0].outstanding_balance = 0.0
    result = apply(
        period=1,
        available_cash=300_000,
        senior_states=states,
        mezz_states=[],
        cash_sweep_pct=1.0,
        dscr_lock_up=False,
    )
    assert result.equity_distribution == pytest.approx(300_000)


def test_equity_locked_up_when_dscr_breach(senior_tranche):
    states = build_states([senior_tranche])
    states[0].outstanding_balance = 0.0
    result = apply(
        period=1,
        available_cash=300_000,
        senior_states=states,
        mezz_states=[],
        cash_sweep_pct=1.0,
        dscr_lock_up=True,
    )
    assert result.equity_distribution == pytest.approx(0.0)
    assert result.dscr_lock_up is True


def test_partial_sweep(senior_tranche):
    states = build_states([senior_tranche])
    result = apply(
        period=1,
        available_cash=500_000,
        senior_states=states,
        mezz_states=[],
        cash_sweep_pct=0.5,
        dscr_lock_up=False,
    )
    assert result.swept_to_senior == pytest.approx(250_000)

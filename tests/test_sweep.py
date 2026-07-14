"""ECF derivation, leverage-banded sweep, and cash-trap.

Methodology Cash Sweep Mechanics: ECF is the cash remaining after ladder steps
1-4 (never an independent formula); the mandatory sweep applies sweep% x ECF per
leverage band; a cash-trap forces the sweep to 100% (retained ECF -> 0).
"""
import pytest

from waterfall.models import sweep
from waterfall.data.schema import SweepConfig, SweepBand


# --- Leverage-banded sweep percentage ------------------------------------
def _cfg():
    return SweepConfig(bands=[SweepBand(3.0, 0.5), SweepBand(4.0, 0.75), SweepBand(5.0, 1.0)],
                       default_sweep_pct=1.0)


def test_band_lookup_picks_tightest_covering_band():
    cfg = _cfg()
    assert sweep.sweep_pct_for_leverage(cfg, 2.5) == pytest.approx(0.5)
    assert sweep.sweep_pct_for_leverage(cfg, 3.5) == pytest.approx(0.75)
    assert sweep.sweep_pct_for_leverage(cfg, 4.5) == pytest.approx(1.0)


def test_band_lookup_above_all_bands_uses_default():
    assert sweep.sweep_pct_for_leverage(_cfg(), 6.0) == pytest.approx(1.0)


def test_no_sweep_config_means_zero_pct():
    assert sweep.sweep_pct_for_leverage(None, 4.0) == pytest.approx(0.0)


# --- Applying the sweep ---------------------------------------------------
def test_apply_sweep_splits_ecf():
    swept, retained = sweep.apply_sweep(ecf_value=200_000, sweep_pct=0.75)
    assert swept == pytest.approx(150_000)
    assert retained == pytest.approx(50_000)


def test_apply_sweep_floors_negative_ecf():
    swept, retained = sweep.apply_sweep(ecf_value=-50_000, sweep_pct=0.75)
    assert swept == pytest.approx(0.0)
    assert retained == pytest.approx(0.0)


def test_cash_trap_forces_100_percent_sweep_no_retained():
    swept, retained = sweep.apply_sweep(ecf_value=200_000, sweep_pct=0.50,
                                        cash_trap=True)
    assert swept == pytest.approx(200_000)   # forced to 100%
    assert retained == pytest.approx(0.0)     # nothing reaches steps 6-7


def test_cash_trap_with_zero_configured_pct_still_sweeps_all():
    swept, retained = sweep.apply_sweep(ecf_value=120_000, sweep_pct=0.0,
                                        cash_trap=True)
    assert swept == pytest.approx(120_000)
    assert retained == pytest.approx(0.0)

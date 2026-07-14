"""Input contract: Deal / Tranche / ReserveConfig / CovenantConfig / Fee / Sweep.

Methodology "Required vs. Optional Parameters" and the Limitations list drive
these. Required omissions raise InvalidInputError (not TypeError); out-of-scope
inputs raise UnsupportedFeatureError.
"""
from datetime import date

import pytest

from waterfall.data.schema import (
    Deal, Tranche, ReserveConfig, CovenantConfig, Fee, SweepConfig, SweepBand,
)
from waterfall.data.exceptions import InvalidInputError, UnsupportedFeatureError


def senior():
    return Tranche(name="Term A", tranche_type="senior", principal=10_000_000.0,
                   coupon=0.06, term_periods=20)


def _deal(**over):
    base = dict(
        deal_close_date=date(2024, 1, 1),
        operations_start_date=date(2024, 1, 1),
        period_frequency="Q",
        tranches=[senior()],
        cfads_stream=[500_000.0, 500_000.0, 500_000.0, 500_000.0],
        data_currency="USD",
        reporting_basis="calendar",
    )
    base.update(over)
    return Deal(**base)


# --- Required parameters --------------------------------------------------
@pytest.mark.parametrize("missing", [
    "deal_close_date", "operations_start_date", "period_frequency",
    "tranches", "cfads_stream", "data_currency", "reporting_basis",
])
def test_missing_required_raises_invalid_input(missing):
    with pytest.raises(InvalidInputError):
        _deal(**{missing: None})


def test_operations_start_before_close_raises():
    with pytest.raises(InvalidInputError):
        _deal(operations_start_date=date(2023, 12, 1), deal_close_date=date(2024, 1, 1))


def test_operations_start_equal_close_is_ok():
    d = _deal(operations_start_date=date(2024, 1, 1), deal_close_date=date(2024, 1, 1))
    assert d.num_periods == 4


def test_bad_period_frequency_raises():
    with pytest.raises(InvalidInputError):
        _deal(period_frequency="weekly")


def test_bad_currency_raises():
    with pytest.raises(InvalidInputError):
        _deal(data_currency="US")
    with pytest.raises(InvalidInputError):
        _deal(data_currency="XYZ")


def test_bad_reporting_basis_raises():
    with pytest.raises(InvalidInputError):
        _deal(reporting_basis="lunar")


def test_empty_tranches_raises():
    with pytest.raises(InvalidInputError):
        _deal(tranches=[])


def test_requires_at_least_one_senior():
    equity = Tranche(name="Equity", tranche_type="equity", principal=5_000_000.0)
    with pytest.raises(InvalidInputError):
        _deal(tranches=[equity])


def test_bad_deal_type_raises():
    with pytest.raises(InvalidInputError):
        _deal(deal_type="MUNICIPAL")


# --- Negative CFADS passes through (methodology MED-5) --------------------
def test_negative_cfads_is_allowed():
    d = _deal(cfads_stream=[500_000.0, -200_000.0, 500_000.0, 500_000.0])
    assert d.cfads_stream[1] == -200_000.0


def test_cfads_must_be_numeric():
    with pytest.raises(InvalidInputError):
        _deal(cfads_stream=[500_000.0, "lots", 500_000.0, 500_000.0])


# --- Out-of-scope inputs raise UnsupportedFeatureError --------------------
def test_b_piece_tranche_out_of_scope():
    with pytest.raises(UnsupportedFeatureError):
        Tranche(name="B", tranche_type="b_piece", principal=1_000_000.0)


def test_preferred_equity_out_of_scope():
    with pytest.raises(UnsupportedFeatureError):
        Tranche(name="Pref", tranche_type="preferred_equity", principal=1_000_000.0)


def test_sculpted_to_dscr_amort_out_of_scope():
    with pytest.raises(UnsupportedFeatureError):
        Tranche(name="T", tranche_type="senior", principal=1_000_000.0,
                amort_type="sculpted_to_dscr")


def test_act_act_day_count_out_of_scope():
    with pytest.raises(UnsupportedFeatureError):
        Tranche(name="T", tranche_type="senior", principal=1_000_000.0,
                day_count="ACT/ACT")


def test_oid_fee_out_of_scope():
    with pytest.raises(UnsupportedFeatureError):
        Fee(fee_type="OID", amount=50_000.0)


def test_multi_currency_tranche_out_of_scope():
    fx = Tranche(name="EUR loan", tranche_type="senior", principal=1_000_000.0,
                 currency="EUR")
    with pytest.raises(UnsupportedFeatureError):
        _deal(tranches=[fx])   # tranche currency != deal data_currency USD


def test_construction_draw_schedule_out_of_scope():
    with pytest.raises(UnsupportedFeatureError):
        _deal(construction_draw_schedule=[100_000.0, 200_000.0])


# --- Config objects validate their own domains ----------------------------
def test_reserve_config_bad_type_raises():
    with pytest.raises(InvalidInputError):
        ReserveConfig(reserve_type="slush_fund")


def test_covenant_config_bad_metric_raises():
    with pytest.raises(InvalidInputError):
        CovenantConfig(metric="vibes", trap=1.10)


def test_covenant_denominator_scope_validated():
    with pytest.raises(InvalidInputError):
        CovenantConfig(metric="DSCR", trap=1.10, denominator="sideways")
    ok = CovenantConfig(metric="DSCR", trap=1.10, denominator="total")
    assert ok.denominator == "total"


def test_sweep_band_pct_bounds():
    with pytest.raises(InvalidInputError):
        SweepBand(max_leverage=5.0, sweep_pct=1.5)


def test_sweep_config_defaults_ordered_bands():
    cfg = SweepConfig(bands=[SweepBand(4.0, 1.0), SweepBand(3.0, 0.5)])
    # Bands are stored sorted ascending by leverage threshold for banded lookup.
    assert [b.max_leverage for b in cfg.bands] == [3.0, 4.0]

"""Every out-of-scope input raises UnsupportedFeatureError (a WaterfallError).

Consolidated coverage of the methodology Limitations list surfaces (B-piece,
preferred equity, multi-currency, construction draw, OID, sculpted-to-DSCR,
ACT/ACT).
"""
from datetime import date

import pytest

from waterfall.data.schema import Deal, Tranche, Fee
from waterfall.models import dates
from waterfall.data.exceptions import UnsupportedFeatureError, WaterfallError


def _base_deal(**over):
    base = dict(
        deal_close_date=date(2024, 1, 1), operations_start_date=date(2024, 1, 1),
        period_frequency="Q",
        tranches=[Tranche("A", "senior", 1_000_000.0, coupon=0.06)],
        cfads_stream=[100_000.0] * 4, data_currency="USD", reporting_basis="calendar",
    )
    base.update(over)
    return Deal(**base)


def test_b_piece():
    with pytest.raises(UnsupportedFeatureError):
        Tranche("B", "b_piece", 1_000_000.0)


def test_preferred_equity():
    with pytest.raises(UnsupportedFeatureError):
        Tranche("Pref", "preferred_equity", 1_000_000.0)


def test_sculpted_to_dscr():
    with pytest.raises(UnsupportedFeatureError):
        Tranche("A", "senior", 1_000_000.0, amort_type="sculpted_to_dscr")


def test_act_act_day_count_on_tranche():
    with pytest.raises(UnsupportedFeatureError):
        Tranche("A", "senior", 1_000_000.0, day_count="ACT/ACT")


def test_act_act_day_count_fraction():
    with pytest.raises(UnsupportedFeatureError):
        dates.day_count_fraction(date(2024, 1, 1), date(2024, 4, 1), "ACT/ACT")


def test_oid_fee():
    with pytest.raises(UnsupportedFeatureError):
        Fee(fee_type="OID", amount=10_000.0)


def test_multi_currency():
    fx = Tranche("EUR", "senior", 1_000_000.0, currency="EUR")
    with pytest.raises(UnsupportedFeatureError):
        _base_deal(tranches=[fx])


def test_construction_draw_schedule():
    with pytest.raises(UnsupportedFeatureError):
        _base_deal(construction_draw_schedule=[100.0, 200.0])


def test_floating_rate_is_rejected_not_silently_fixed():
    # M2: floating/step-up accrual is out of v0.x scope -> fail loud rather than
    # silently model the tranche as a fixed coupon.
    with pytest.raises(UnsupportedFeatureError):
        Tranche("A", "senior", 1_000_000.0, coupon=0.06, rate_type="floating")


def test_step_up_rate_is_rejected():
    with pytest.raises(UnsupportedFeatureError):
        Tranche("A", "senior", 1_000_000.0, coupon=0.06, rate_type="step_up")


def test_all_out_of_scope_are_waterfall_errors():
    assert issubclass(UnsupportedFeatureError, WaterfallError)

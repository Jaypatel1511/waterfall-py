"""Tranche state: schedules, interest accrual, amortization, prepay, draws.

Methodology: interest = rate x average balance x day-count fraction; principal
trace opening + facility draws - scheduled amort - prepayments - sweeps = closing.
"""
import math
from datetime import date

import pytest

from waterfall.data.schema import Tranche
from waterfall.models import tranches, dates


def _senior(**over):
    base = dict(name="Term A", tranche_type="senior", principal=1_000_000.0,
                coupon=0.06, day_count=dates.ACT_360)
    base.update(over)
    return Tranche(**base)


# --- Amortization schedules ----------------------------------------------
def test_bullet_schedule_pays_principal_at_maturity():
    sched = tranches.build_schedule(_senior(amort_type="bullet", term_periods=4),
                                    horizon_periods=4)
    assert sched[:3] == [0.0, 0.0, 0.0]
    assert sched[3] == pytest.approx(1_000_000.0)


def test_fully_amortizing_is_level_principal():
    sched = tranches.build_schedule(_senior(amort_type="fully_amortizing", term_periods=4),
                                    horizon_periods=4)
    assert sched == pytest.approx([250_000.0] * 4)


def test_io_then_amortize():
    sched = tranches.build_schedule(
        _senior(amort_type="fully_amortizing", term_periods=4, io_periods=2),
        horizon_periods=4)
    assert sched[0] == 0.0 and sched[1] == 0.0
    assert sched[2] == pytest.approx(500_000.0)
    assert sched[3] == pytest.approx(500_000.0)
    assert sum(sched) == pytest.approx(1_000_000.0)


def test_balloon_30_due_in_10_leaves_balance_at_maturity():
    # Amortize over 40 periods but mature at 4 -> balloon of the remaining balance.
    sched = tranches.build_schedule(
        _senior(amort_type="balloon", term_periods=4, amort_periods=40),
        horizon_periods=4)
    # First 3 periods amortize a small slice; period 4 repays the whole remaining.
    assert sched[0] == pytest.approx(25_000.0)   # 1,000,000 / 40
    assert sum(sched) == pytest.approx(1_000_000.0)
    assert sched[3] > sched[0]                   # balloon is large


def test_custom_schedule_used_verbatim():
    sched = tranches.build_schedule(
        _senior(amort_type="custom", term_periods=4,
                custom_principal=[100_000.0, 200_000.0, 300_000.0, 400_000.0]),
        horizon_periods=4)
    assert sched == pytest.approx([100_000.0, 200_000.0, 300_000.0, 400_000.0])


def test_mortgage_constant_grows_principal_component():
    sched = tranches.build_schedule(
        _senior(amort_type="mortgage", term_periods=4, coupon=0.10),
        horizon_periods=4)
    # Level-payment mortgage: principal component increases each period.
    assert sched[0] < sched[1] < sched[2] < sched[3]
    assert sum(sched) == pytest.approx(1_000_000.0, rel=1e-9)


# --- Interest accrual -----------------------------------------------------
def test_interest_is_rate_times_balance_times_dcf():
    st = tranches.TrancheState(_senior(), horizon_periods=4)
    dcf = dates.day_count_fraction(date(2024, 1, 1), date(2024, 4, 1), dates.ACT_360)
    accrued = st.accrue_interest(dcf)
    assert accrued == pytest.approx(0.06 * 1_000_000.0 * dcf)


def test_pik_capitalizes_interest_to_principal():
    st = tranches.TrancheState(_senior(tranche_type="mezzanine", pik=True), horizon_periods=4)
    dcf = dates.day_count_fraction(date(2024, 1, 1), date(2024, 4, 1), dates.ACT_360)
    accrued = st.accrue_interest(dcf)
    cap = st.capitalize_pik(accrued)
    assert cap == pytest.approx(accrued)
    assert st.balance == pytest.approx(1_000_000.0 + accrued)


# --- Payment mechanics + principal trace ----------------------------------
def test_pay_interest_records_shortfall_when_cash_short():
    st = tranches.TrancheState(_senior(), horizon_periods=4)
    dcf = dates.day_count_fraction(date(2024, 1, 1), date(2024, 4, 1), dates.ACT_360)
    due = st.accrue_interest(dcf)
    paid, remaining, shortfall = st.pay_interest(due, available=due / 2)
    assert paid == pytest.approx(due / 2)
    assert remaining == pytest.approx(0.0)
    assert shortfall == pytest.approx(due / 2)


def test_principal_trace_ties_out_across_movements():
    st = tranches.TrancheState(_senior(), horizon_periods=4)
    opening = st.balance
    draw = st.draw(200_000.0)
    sched = st.pay_scheduled_principal(150_000.0, available=1e9)[0]
    sweep = st.apply_prepayment(100_000.0, category="sweep")
    prepay = st.apply_prepayment(50_000.0, category="proceeds")
    closing = st.balance
    # opening + draws - scheduled - sweeps - prepayments == closing
    assert opening + draw - sched - sweep - prepay == pytest.approx(closing)


def test_scheduled_principal_capped_at_balance():
    st = tranches.TrancheState(_senior(principal=100_000.0), horizon_periods=4)
    paid, _, _ = st.pay_scheduled_principal(999_999.0, available=1e9)
    assert paid == pytest.approx(100_000.0)   # never over-amortize past the balance
    assert st.balance == pytest.approx(0.0)

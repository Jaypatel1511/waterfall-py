"""Prepayment re-amortization (audit H1; methodology LOCKED line 51).

Default behavior is to RE-AMORTIZE the remaining schedule over the remaining term
after a prepayment/sweep; the ``recompute_on_prepayment=False`` knob keeps the
original installment (loan shortens instead). A higher interim scheduled principal
(the no-reamort path) raises senior debt service and therefore LOWERS DSCR — the
exact way the bug manufactured false covenant pressure.
"""
from datetime import date

import pytest

from waterfall import run
from waterfall.data.schema import Deal, Tranche, CovenantConfig
from waterfall.models import tranches

DC = "30/360"
_TD = dict(deal_close_date=date(2024, 1, 1), operations_start_date=date(2024, 1, 1),
           period_frequency="A", data_currency="USD", reporting_basis="calendar")


# --- Unit: the schedule re-levels on the reduced balance ------------------
def test_reamortize_relevels_remaining_installments():
    t = Tranche("Term A", "senior", 1_000_000.0, coupon=0.05, day_count=DC,
                amort_type="fully_amortizing", term_periods=4)
    st = tranches.TrancheState(t, horizon_periods=4, periods_per_year=1)
    assert st.schedule == pytest.approx([250_000.0] * 4)      # 1,000,000 over 4
    st.apply_prepayment(400_000.0, "sweep", period_index=0)
    assert st.balance == pytest.approx(600_000.0)
    # 600,000 re-amortized over the remaining 3 periods = 200,000 each.
    assert st.schedule[1:] == pytest.approx([200_000.0, 200_000.0, 200_000.0])


def test_keep_installment_knob_leaves_schedule_unchanged():
    t = Tranche("Term A", "senior", 1_000_000.0, coupon=0.05, day_count=DC,
                amort_type="fully_amortizing", term_periods=4,
                recompute_on_prepayment=False)
    st = tranches.TrancheState(t, horizon_periods=4, periods_per_year=1)
    st.apply_prepayment(400_000.0, "sweep", period_index=0)
    assert st.balance == pytest.approx(600_000.0)
    # Installments stay at 250,000 (loan simply retires a period early).
    assert st.schedule[1:] == pytest.approx([250_000.0, 250_000.0, 250_000.0])


# --- Integration: re-amort vs keep-installment give different DSCR --------
# 10M senior fully-amortizing over 5; a one-time 3,000,000 event-proceeds
# prepayment at t0 reduces the balance to 5,000,000 (2M scheduled + 3M proceeds).
def _deal(recompute):
    senior = Tranche("Term A", "senior", 10_000_000.0, coupon=0.05, day_count=DC,
                     amort_type="fully_amortizing", term_periods=5,
                     recompute_on_prepayment=recompute)
    equity = Tranche("Equity", "equity", 2_000_000.0)
    return Deal(**_TD, deal_type="PF", tranches=[senior, equity],
                cfads_stream=[6_000_000.0] * 5,
                event_proceeds=[3_000_000.0, 0.0, 0.0, 0.0, 0.0],
                covenants=[CovenantConfig(metric="DSCR", performance=1.20)])


def test_reamortized_schedule_lowers_scheduled_ds_and_shifts_dscr():
    reamort = run(_deal(True))
    keep = run(_deal(False))

    p1_re, p1_keep = reamort.periods[1], keep.periods[1]
    # Re-amortize: 5,000,000 over the remaining 4 periods -> 1,250,000 each.
    assert p1_re.principal_by_tranche["Term A"] == pytest.approx(1_250_000.0)
    # Keep-installment: the original 2,000,000 installment stands.
    assert p1_keep.principal_by_tranche["Term A"] == pytest.approx(2_000_000.0)
    # Lower scheduled principal -> lower senior DS -> HIGHER DSCR under re-amort.
    assert p1_re.dscr == pytest.approx(6_000_000.0 / 1_500_000.0)   # 4.00
    assert p1_keep.dscr == pytest.approx(6_000_000.0 / 2_250_000.0)  # 2.667
    assert p1_re.dscr > p1_keep.dscr

"""Prepayment applies strictly senior-first, never pari-passu across seniority
(audit H3; methodology step 5 + separate proceeds path).

The pre-fix engine split a sweep/proceeds prepayment pro-rata across senior AND
mezz together, retiring mezzanine alongside senior — a seniority violation. Both
the ECF sweep and the proceeds path must exhaust the senior group before touching
mezzanine.

Deal: 3,000,000 senior + 1,000,000 mezz, both bullet; a 100% sweep every period.
Annual / 30/360 -> interest is exactly coupon x balance.
"""
from datetime import date

import pytest

from waterfall import run
from waterfall.data.schema import (
    Deal, Tranche, SweepConfig, SweepBand, CovenantConfig,
)

DC = "30/360"
_TD = dict(deal_close_date=date(2024, 1, 1), operations_start_date=date(2024, 1, 1),
           period_frequency="A", data_currency="USD", reporting_basis="calendar")


def _deal(via_proceeds=False):
    senior = Tranche("Term A", "senior", 3_000_000.0, coupon=0.05, day_count=DC,
                     amort_type="bullet", term_periods=8)
    mezz = Tranche("Mezz", "mezzanine", 1_000_000.0, coupon=0.10, day_count=DC,
                   amort_type="bullet", term_periods=8)
    equity = Tranche("Equity", "equity", 1_000_000.0)
    kw = dict(**_TD, deal_type="PF", tranches=[senior, mezz, equity],
              cfads_stream=[2_000_000.0] * 8,
              covenants=[CovenantConfig(metric="DSCR", performance=1.10)])
    if via_proceeds:
        kw["event_proceeds"] = [3_500_000.0] + [0.0] * 7
    else:
        kw["sweep"] = SweepConfig(bands=[SweepBand(100.0, 1.0)], default_sweep_pct=1.0)
    return Deal(**kw)


def test_ecf_sweep_prepays_senior_before_touching_mezz():
    r = run(_deal())

    # t0: ECF = 2,000,000 - 150,000 senior int - 100,000 mezz int = 1,750,000,
    # swept entirely to SENIOR; mezz principal untouched while senior remains.
    p0 = r.periods[0]
    assert p0.sweep_amount == pytest.approx(1_750_000.0)
    assert p0.principal_by_tranche["Term A"] == pytest.approx(1_750_000.0)
    assert p0.principal_by_tranche["Mezz"] == pytest.approx(0.0)

    # t1: senior balance is 1,250,000; the sweep retires it (1,250,000) and only the
    # REMAINDER (587,500) reaches mezz — mezz is touched only after senior is gone.
    p1 = r.periods[1]
    assert p1.principal_by_tranche["Term A"] == pytest.approx(1_250_000.0)
    assert p1.principal_by_tranche["Mezz"] == pytest.approx(587_500.0)


def test_event_proceeds_apply_in_strict_priority_order():
    # 3,500,000 of proceeds at t0: 3,000,000 retires senior, only the 500,000
    # overflow reaches mezz.
    r = run(_deal(via_proceeds=True))
    p0 = r.periods[0]
    assert p0.principal_by_tranche["Term A"] == pytest.approx(3_000_000.0)
    assert p0.principal_by_tranche["Mezz"] == pytest.approx(500_000.0)

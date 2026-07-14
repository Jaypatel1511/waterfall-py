"""Tranche state and amortization mechanics.

Interest accrues as ``coupon x balance x day-count-fraction`` (the interest-
reconciliation assertion recomputes exactly this). Principal movements are
tracked by category so the principal-trace assertion can tie out:

    opening + facility draws - scheduled amort - prepayments - sweeps = closing

Prepayment default is "no re-amortization": a scheduled installment is capped at
the remaining balance, so early prepayment simply retires the loan sooner (the
trace still balances). Re-amortization on prepayment is deferred (documented).
"""
from typing import List

from waterfall.data.schema import Tranche


def build_schedule(tranche: Tranche, horizon_periods: int,
                   periods_per_year: int = 1) -> List[float]:
    """Scheduled principal per period over the deal horizon.

    ``term_periods`` is maturity (default = horizon); ``amort_periods`` is the
    amortization term (default = term); ``amort_periods > term_periods`` leaves a
    balloon at maturity ("30-due-in-10"). ``io_periods`` are leading
    interest-only periods.
    """
    n = horizon_periods
    P = float(tranche.principal)
    sched = [0.0] * n
    if tranche.tranche_type == "equity" or P <= 0:
        return sched

    term = tranche.term_periods or n
    term = min(term, n)
    amort = tranche.amort_periods or term
    io = tranche.io_periods

    if tranche.amort_type == "custom":
        custom = tranche.custom_principal or []
        for i, v in enumerate(custom[:n]):
            sched[i] = float(v)
        return sched

    # Entirely interest-only within the term, or bullet/io -> balloon at maturity.
    amort_window = amort - io
    if tranche.amort_type in ("bullet", "io") or amort_window <= 0 or term - io <= 0:
        sched[term - 1] += P
        return sched

    installments = _installments(tranche.amort_type, P, amort_window,
                                 tranche.coupon / periods_per_year)

    remaining = P
    for i in range(io, term):
        if i == term - 1:
            sched[i] = remaining          # maturity: repay the remaining balance (balloon)
            remaining = 0.0
        else:
            pay = min(installments[i - io], remaining)
            sched[i] = pay
            remaining -= pay
    return sched


def _installments(amort_type: str, principal: float, window: int,
                  periodic_rate: float) -> List[float]:
    """Principal component of each installment over the full amortization window."""
    if amort_type in ("fully_amortizing", "balloon") or periodic_rate == 0:
        level = principal / window
        return [level] * window
    # mortgage constant: level total payment, principal component grows each period.
    r = periodic_rate
    payment = principal * r / (1 - (1 + r) ** (-window))
    out = []
    bal = principal
    for _ in range(window):
        interest = bal * r
        principal_component = payment - interest
        out.append(principal_component)
        bal -= principal_component
    return out


class TrancheState:
    """Mutable per-period state for one tranche."""

    def __init__(self, tranche: Tranche, horizon_periods: int,
                 periods_per_year: int = 1):
        self.tranche = tranche
        self.balance = float(tranche.principal)
        self.schedule = build_schedule(tranche, horizon_periods, periods_per_year)

    # --- identity helpers ---
    @property
    def name(self) -> str:
        return self.tranche.name

    @property
    def is_paid_off(self) -> bool:
        return self.balance <= 1e-9

    # --- interest ---
    def accrue_interest(self, dcf: float) -> float:
        """Interest for the period = coupon x current balance x day-count fraction."""
        return self.tranche.coupon * self.balance * dcf

    def capitalize_pik(self, amount: float) -> float:
        """Capitalize PIK interest into principal; returns the amount capitalized."""
        self.balance += amount
        return amount

    def pay_interest(self, due: float, available: float):
        """Pay interest from ``available``; returns (paid, remaining_cash, shortfall)."""
        avail = max(available, 0.0)
        paid = min(due, avail)
        return paid, available - paid, due - paid

    # --- principal ---
    def scheduled_principal_due(self, period_index: int) -> float:
        due = self.schedule[period_index] if period_index < len(self.schedule) else 0.0
        return min(due, self.balance)

    def pay_scheduled_principal(self, due: float, available: float):
        """Pay scheduled principal (capped at balance) from ``available``.

        Returns (paid, remaining_cash, shortfall).
        """
        due = min(due, self.balance)
        avail = max(available, 0.0)
        paid = min(due, avail)
        self.balance -= paid
        return paid, available - paid, due - paid

    def apply_prepayment(self, amount: float, category: str) -> float:
        """Apply a prepayment/sweep (capped at balance); returns the amount applied.

        ``category`` labels the movement for the principal trace: "sweep" for the
        step-5 ECF sweep, "proceeds" for the separate proceeds path / mandatory
        prepayments.
        """
        applied = min(max(amount, 0.0), self.balance)
        self.balance -= applied
        return applied

    def draw(self, amount: float) -> float:
        """Facility draw (revolver / delayed-draw): increases the balance."""
        amount = max(amount, 0.0)
        self.balance += amount
        return amount

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
from waterfall.data.exceptions import InvalidInputError


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
        # Cumulative amount drawn against a facility's commitment. The at-close
        # opening balance (the funded amount in v0.x) counts as the first draw, so
        # further draws are capped at the undrawn commitment (see draw()).
        self._drawn_total = self.balance
        self._ppy = periods_per_year
        # Resolved schedule geometry (mirrors build_schedule) — kept so the
        # schedule can be re-amortized over the remaining term on prepayment.
        term = tranche.term_periods or horizon_periods
        self._term = min(term, horizon_periods)
        self._amort = tranche.amort_periods or self._term
        self._io = tranche.io_periods
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

    def apply_prepayment(self, amount: float, category: str,
                         period_index: int = None) -> float:
        """Apply a prepayment/sweep (capped at balance); returns the amount applied.

        ``category`` labels the movement for the principal trace: "sweep" for the
        step-5 ECF sweep, "proceeds" for the separate proceeds path / mandatory
        prepayments. When ``recompute_on_prepayment`` is set (methodology default)
        and ``period_index`` is supplied, the remaining schedule is re-amortized
        over the remaining term on the reduced balance.
        """
        applied = min(max(amount, 0.0), self.balance)
        self.balance -= applied
        if (applied > 0 and period_index is not None
                and self.tranche.recompute_on_prepayment and self.balance > 1e-9):
            self._reamortize(period_index)
        return applied

    def _reamortize(self, from_period: int) -> None:
        """Rebuild ``schedule[from_period+1:]`` so the reduced balance amortizes over
        the remaining term (methodology "recompute on prepayment: default re-amortize").

        Bullet/IO tranches still balloon the whole balance at maturity (re-amort is a
        no-op on their profile). Amortizing tranches re-level on the new balance over
        the remaining amortization window, leaving any balloon at maturity smaller.
        """
        n = len(self.schedule)
        term, io = self._term, self._io
        if from_period >= term - 1:
            return  # at/after maturity: nothing left to reschedule
        for i in range(from_period + 1, n):
            self.schedule[i] = 0.0
        if self.balance <= 0:
            return
        start = max(from_period + 1, io)
        amort_window = self._amort - io
        if self.tranche.amort_type in ("bullet", "io") or amort_window <= 0 or term - io <= 0:
            self.schedule[term - 1] = self.balance   # balloon the remaining balance
            return
        elapsed = max(0, (from_period + 1) - io)
        remaining_window = max(amort_window - elapsed, 1)
        rate = self.tranche.coupon / self._ppy
        installments = _installments(self.tranche.amort_type, self.balance,
                                     remaining_window, rate)
        remaining = self.balance
        for k, i in enumerate(range(start, term)):
            if i == term - 1:
                self.schedule[i] = remaining          # maturity: repay remaining (balloon)
                remaining = 0.0
            else:
                inst = installments[k] if k < len(installments) else remaining
                pay = min(inst, remaining)
                self.schedule[i] = pay
                remaining -= pay

    def draw(self, amount: float) -> float:
        """Facility draw (revolver / delayed-draw): increases the balance.

        Enforces the commitment cap (methodology Capital Stack — "the commitment
        cap is enforced"): cumulative draws (the at-close opening balance plus any
        further draw) must not exceed the tranche's ``commitment``. A draw that
        would breach it raises :class:`InvalidInputError` rather than silently
        over-funding. A facility with no ``commitment`` set is uncapped.

        In v0.x a non-zero ``facility_draws`` schedule is rejected at input
        validation (mid-life draws deferred to v0.1), so the engine never calls
        this during a run; the cap is a hard guard on the primitive itself.
        """
        amount = max(amount, 0.0)
        commitment = self.tranche.commitment
        if commitment is not None and self._drawn_total + amount > commitment + 1e-6:
            raise InvalidInputError(
                f"tranche {self.name!r}: draw {amount:,.2f} would push cumulative "
                f"draws to {self._drawn_total + amount:,.2f}, above the commitment "
                f"{commitment:,.2f}"
            )
        self._drawn_total += amount
        self.balance += amount
        return amount

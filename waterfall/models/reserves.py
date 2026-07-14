"""Reserve account mechanics (DSRA/IRA/MRA/capex/lease_up/TI_LC).

Per the methodology:
- **Draw**: when CFADS is short of senior debt service (step 2), the reserve is
  drawn to cover the shortfall (down to zero). Draws are a cash *source*.
- **Replenish**: topped back up to the required balance at waterfall step 3.
- **Top-up**: discretionary top-ups at step 6b (a cash *use*).
- **Release**: full balance released on trigger / at maturity, onto the separate
  proceeds path (not swept as ECF). Releases are a cash *source*.

Roll-forward (per reserve, per period):
    closing = opening + required funding (step 3) + top-ups (step 6b) - draws - releases

``lc_funded`` reserves have no pre-funded cash; the letter of credit provides
capacity available for a shortfall (the draw injects cash from the LC provider).
"""
from waterfall.data.schema import ReserveConfig


def dsra_required(months: int, periodic_senior_ds: float, months_per_period: int) -> float:
    """Required DSRA balance = ``months`` months of senior debt service.

    ``periodic_senior_ds`` is the senior debt service for one period of length
    ``months_per_period`` months.
    """
    monthly_ds = periodic_senior_ds / months_per_period
    return months * monthly_ds


class ReserveState:
    """Mutable per-period state for one reserve account."""

    def __init__(self, config: ReserveConfig, required_balance=None):
        self.config = config
        self.reserve_type = config.reserve_type
        self.lc_funded = config.lc_funded
        self.required = (required_balance if required_balance is not None
                         else (config.target_amount or 0.0))
        if config.lc_funded:
            # No pre-funded cash; the LC provides capacity up to the required size.
            self.balance = max(config.opening_balance, self.required)
        else:
            self.balance = config.opening_balance

    def set_required(self, amount: float) -> None:
        self.required = max(amount, 0.0)

    def draw(self, shortfall: float) -> float:
        """Cover ``shortfall`` from the reserve (down to zero); return amount drawn."""
        drawn = min(max(shortfall, 0.0), self.balance)
        self.balance -= drawn
        return drawn

    def replenish(self, available: float):
        """Top up to the required balance from ``available``.

        Returns (funded, remaining_cash).
        """
        need = max(self.required - self.balance, 0.0)
        funded = min(need, max(available, 0.0))
        self.balance += funded
        return funded, available - funded

    def top_up(self, amount: float) -> float:
        """Discretionary top-up (step 6b); returns amount added."""
        amount = max(amount, 0.0)
        self.balance += amount
        return amount

    def topup_room(self) -> float:
        """Step-6b headroom: distance to the discretionary target, capped per period.

        Zero unless a ``discretionary_target`` is configured (6a/6b are opt-in).
        """
        target = self.config.discretionary_target
        if target is None:
            return 0.0
        room = max(target - self.balance, 0.0)
        cap = self.config.topup_cap_per_period
        if cap is not None:
            room = min(room, cap)
        return room

    def discretionary_top_up(self, available: float) -> float:
        """Apply a step-6b discretionary top-up from ``available`` (capped at the
        room to the discretionary target). Returns the amount added."""
        added = min(max(available, 0.0), self.topup_room())
        self.balance += added
        return added

    def release(self) -> float:
        """Release the full balance (trigger/maturity); returns released cash."""
        released = self.balance
        self.balance = 0.0
        return released

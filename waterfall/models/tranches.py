from dataclasses import dataclass
from typing import Optional
import pandas as pd

from waterfall.data.schema import Tranche


@dataclass
class TrancheState:
    """Tracks the live state of a tranche across periods."""
    tranche: Tranche
    outstanding_balance: float
    total_interest_paid: float = 0.0
    total_principal_paid: float = 0.0
    periods_in_default: int = 0

    @property
    def name(self) -> str:
        return self.tranche.name

    @property
    def is_paid_off(self) -> bool:
        return self.outstanding_balance <= 0.01

    def accrue_interest(self) -> float:
        """Return interest due this period."""
        if self.is_paid_off:
            return 0.0
        return self.outstanding_balance * self.tranche.rate

    def accrue_pik(self) -> float:
        """Add PIK interest to principal (mezz only)."""
        if not self.tranche.is_mezz or self.tranche.pik_rate == 0:
            return 0.0
        pik = self.outstanding_balance * self.tranche.pik_rate
        self.outstanding_balance += pik
        return pik

    def pay_interest(self, available_cash: float) -> tuple:
        """
        Pay as much interest as possible from available cash.
        Returns (interest_paid, remaining_cash).
        """
        due = self.accrue_interest()
        paid = min(due, available_cash)
        self.total_interest_paid += paid
        shortfall = due - paid
        return paid, available_cash - paid, shortfall

    def pay_principal(self, available_cash: float,
                      amount: Optional[float] = None) -> tuple:
        """
        Pay scheduled or specified principal from available cash.
        Returns (principal_paid, remaining_cash).
        """
        if self.tranche.is_equity or self.is_paid_off:
            return 0.0, available_cash, 0.0
        scheduled = amount if amount is not None \
            else self.tranche.scheduled_annual_principal
        due = min(scheduled, self.outstanding_balance)
        paid = min(due, available_cash)
        self.outstanding_balance -= paid
        self.total_principal_paid += paid
        shortfall = due - paid
        return paid, available_cash - paid, shortfall

    def sweep(self, available_cash: float, pct: float = 1.0) -> tuple:
        """
        Apply cash sweep — prepay principal with excess cash.
        Returns (swept_amount, remaining_cash).
        """
        if self.tranche.is_equity or self.is_paid_off:
            return 0.0, available_cash
        sweep_amount = min(
            available_cash * pct,
            self.outstanding_balance
        )
        self.outstanding_balance -= sweep_amount
        self.total_principal_paid += sweep_amount
        return sweep_amount, available_cash - sweep_amount


def build_states(tranches: list) -> list:
    """Initialize TrancheState objects from a list of Tranche objects."""
    return [
        TrancheState(
            tranche=t,
            outstanding_balance=t.principal
        )
        for t in tranches
    ]

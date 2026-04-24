from dataclasses import dataclass, field
from typing import Optional


@dataclass
class Tranche:
    """
    Represents a single debt or equity tranche in the capital stack.
    """
    name: str
    principal: float          # original principal in dollars
    rate: float               # annual interest rate e.g. 0.06
    term_years: int           # amortization term in years
    priority: int             # 1 = highest priority
    is_mezz: bool = False     # True for mezzanine/subordinated debt
    is_equity: bool = False   # True for equity tranche
    pik_rate: float = 0.0     # paid-in-kind rate for mezz (adds to principal)

    def __post_init__(self):
        if self.principal <= 0:
            raise ValueError(f"Tranche '{self.name}': principal must be positive")
        if not (0 <= self.rate < 1):
            raise ValueError(f"Tranche '{self.name}': rate must be between 0 and 1")
        if self.term_years <= 0:
            raise ValueError(f"Tranche '{self.name}': term_years must be positive")
        if self.priority < 1:
            raise ValueError(f"Tranche '{self.name}': priority must be >= 1")

    @property
    def annual_interest(self) -> float:
        return self.principal * self.rate

    @property
    def scheduled_annual_principal(self) -> float:
        if self.is_equity:
            return 0.0
        return self.principal / self.term_years


@dataclass
class CashFlowPeriod:
    """
    Represents cash flow available for debt service in a single period.
    """
    period: int               # period number (1-indexed)
    cfads: float              # cash flow available for debt service
    operating_expenses: float = 0.0

    def __post_init__(self):
        if self.period < 1:
            raise ValueError("period must be >= 1")
        if self.cfads < 0:
            raise ValueError(f"Period {self.period}: cfads cannot be negative")


@dataclass
class DealStructure:
    """
    Core input contract for a waterfall model.
    Combines tranches, cash flow periods, and deal parameters.
    """
    name: str
    tranches: list            # list of Tranche objects
    cash_flows: list          # list of CashFlowPeriod objects
    min_dscr: float = 1.25   # minimum DSCR covenant
    dsra_months: int = 6      # DSRA target in months of debt service
    cash_sweep_pct: float = 1.0  # % of excess cash swept e.g. 1.0 = 100%

    def __post_init__(self):
        if not self.tranches:
            raise ValueError("DealStructure must have at least one tranche")
        if not self.cash_flows:
            raise ValueError("DealStructure must have at least one cash flow period")
        if self.min_dscr <= 0:
            raise ValueError("min_dscr must be positive")
        if not (0 <= self.cash_sweep_pct <= 1):
            raise ValueError("cash_sweep_pct must be between 0 and 1")

        # Sort tranches by priority
        self.tranches = sorted(self.tranches, key=lambda t: t.priority)

    @property
    def total_debt(self) -> float:
        return sum(t.principal for t in self.tranches if not t.is_equity)

    @property
    def total_equity(self) -> float:
        return sum(t.principal for t in self.tranches if t.is_equity)

    @property
    def senior_tranches(self) -> list:
        return [t for t in self.tranches if not t.is_mezz and not t.is_equity]

    @property
    def mezz_tranches(self) -> list:
        return [t for t in self.tranches if t.is_mezz]

    @property
    def equity_tranches(self) -> list:
        return [t for t in self.tranches if t.is_equity]

    @property
    def num_periods(self) -> int:
        return len(self.cash_flows)

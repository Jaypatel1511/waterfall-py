from dataclasses import dataclass
import pandas as pd


@dataclass
class SweepResult:
    """Result of cash sweep logic for a single period."""
    period: int
    cash_before_sweep: float
    swept_to_senior: float
    swept_to_mezz: float
    cash_after_sweep: float
    equity_distribution: float
    dscr_lock_up: bool


def apply(
    period: int,
    available_cash: float,
    senior_states: list,
    mezz_states: list,
    cash_sweep_pct: float,
    dscr_lock_up: bool,
) -> SweepResult:
    """
    Apply cash sweep and equity distribution logic.

    Priority:
    1. Sweep excess cash to senior debt principal
    2. Sweep remaining to mezz debt principal
    3. Distribute remainder to equity (if not locked up)

    Args:
        period:           Current period
        available_cash:   Cash remaining after all debt service
        senior_states:    List of senior TrancheState objects
        mezz_states:      List of mezz TrancheState objects
        cash_sweep_pct:   Fraction of excess cash to sweep (e.g. 1.0)
        dscr_lock_up:     If True, block equity distributions

    Returns:
        SweepResult with sweep amounts and equity distribution
    """
    cash = available_cash
    swept_senior = 0.0
    swept_mezz = 0.0

    # Sweep to senior tranches first
    for state in senior_states:
        if cash <= 0:
            break
        swept, cash = state.sweep(cash, pct=cash_sweep_pct)
        swept_senior += swept

    # Then sweep to mezz
    for state in mezz_states:
        if cash <= 0:
            break
        swept, cash = state.sweep(cash, pct=cash_sweep_pct)
        swept_mezz += swept

    # Equity distribution only if not locked up
    equity_distribution = 0.0
    if not dscr_lock_up and cash > 0:
        equity_distribution = cash
        cash = 0.0

    return SweepResult(
        period=period,
        cash_before_sweep=available_cash,
        swept_to_senior=swept_senior,
        swept_to_mezz=swept_mezz,
        cash_after_sweep=cash,
        equity_distribution=equity_distribution,
        dscr_lock_up=dscr_lock_up,
    )

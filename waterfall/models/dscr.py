from dataclasses import dataclass
from typing import Optional
import pandas as pd


@dataclass
class DSCRResult:
    """Tracks DSCR across all periods."""
    period: int
    cfads: float
    total_debt_service: float
    dscr: float
    min_dscr: float
    covenant_breach: bool
    lock_up: bool          # equity distributions locked
    default: bool          # DSCR below 1.0

    @property
    def status(self) -> str:
        if self.default:
            return "DEFAULT"
        if self.covenant_breach:
            return "LOCK-UP"
        return "OK"


def calculate(
    period: int,
    cfads: float,
    total_debt_service: float,
    min_dscr: float,
    lockup_dscr: Optional[float] = None,
) -> DSCRResult:
    """
    Calculate DSCR for a single period and assess covenant compliance.

    Args:
        period:            Period number
        cfads:             Cash flow available for debt service
        total_debt_service: Total interest + principal due
        min_dscr:          Minimum DSCR covenant (e.g. 1.25)
        lockup_dscr:       DSCR below which equity is locked up
                           Defaults to min_dscr if not provided

    Returns:
        DSCRResult with DSCR and covenant flags
    """
    if lockup_dscr is None:
        lockup_dscr = min_dscr

    if total_debt_service <= 0:
        dscr = float("inf")
    else:
        dscr = cfads / total_debt_service

    covenant_breach = dscr < min_dscr
    lock_up = dscr < lockup_dscr
    default = dscr < 1.0

    return DSCRResult(
        period=period,
        cfads=cfads,
        total_debt_service=total_debt_service,
        dscr=dscr,
        min_dscr=min_dscr,
        covenant_breach=covenant_breach,
        lock_up=lock_up,
        default=default,
    )


def summary_table(dscr_results: list) -> pd.DataFrame:
    """Return a DataFrame summarizing DSCR across all periods."""
    rows = []
    for r in dscr_results:
        rows.append({
            "Period": r.period,
            "CFADS ($)": f"${r.cfads:,.0f}",
            "Debt Service ($)": f"${r.total_debt_service:,.0f}",
            "DSCR": f"{r.dscr:.2f}x" if r.dscr != float('inf') else "N/A",
            "Status": r.status,
        })
    return pd.DataFrame(rows)



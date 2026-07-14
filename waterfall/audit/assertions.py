"""The six validation assertions — the primary numeric-defensibility mechanism.

Each raises a typed exception (never silently swallows). Tolerance is absolute
with a small relative allowance so cent-level floating error passes while genuine
imbalances (the corrupted-ledger tests) fire.
"""
from waterfall.audit.log import PeriodLedger
from waterfall.data.exceptions import (
    SourceUseImbalanceError,
    WaterfallImbalanceError,
    PrincipalTraceError,
    InterestReconciliationError,
    ReserveRollForwardError,
    CapitalAccountError,
)

_TOL_ABS = 1e-4
_TOL_REL = 1e-9


def _close(a: float, b: float) -> bool:
    return abs(a - b) <= _TOL_ABS + _TOL_REL * max(abs(a), abs(b))


def assert_source_use_close(sources: float, uses: float) -> None:
    """Source/use tie-out at close."""
    if not _close(sources, uses):
        raise SourceUseImbalanceError(
            f"close source/use imbalance: sources {sources:.6f} != uses {uses:.6f}"
        )


def assert_cash_conservation(ledger: PeriodLedger) -> None:
    """General period cash-conservation: sum(all sources) = sum(all uses).

    Both sides are enumerated from the actual per-period ledger, so any modeled
    mechanism is covered without a hardcoded source/use list.
    """
    s, u = ledger.total_sources(), ledger.total_uses()
    if not _close(s, u):
        raise WaterfallImbalanceError(
            f"period {ledger.period_index}: cash imbalance "
            f"sources {s:.6f} != uses {u:.6f} (diff {s - u:.6f})"
        )


def assert_principal_trace(tranche_name: str, period_index: int, opening: float,
                           draws: float, scheduled: float, prepayments: float,
                           sweeps: float, closing: float) -> None:
    """opening + facility draws - scheduled amort - prepayments - sweeps = closing."""
    expected = opening + draws - scheduled - prepayments - sweeps
    if not _close(expected, closing):
        raise PrincipalTraceError(
            f"period {period_index} tranche {tranche_name!r}: principal trace "
            f"{expected:.6f} != closing {closing:.6f}"
        )


def assert_interest_reconciliation(tranche_name: str, period_index: int,
                                   coupon: float, avg_balance: float, dcf: float,
                                   booked_interest: float) -> None:
    """rate x average balance x day-count fraction = period interest."""
    expected = coupon * avg_balance * dcf
    if not _close(expected, booked_interest):
        raise InterestReconciliationError(
            f"period {period_index} tranche {tranche_name!r}: interest "
            f"{expected:.6f} != booked {booked_interest:.6f}"
        )


def assert_reserve_roll_forward(reserve_type: str, period_index: int, opening: float,
                                funding: float, topups: float, draws: float,
                                releases: float, closing: float) -> None:
    """closing = opening + required funding (3) + top-ups (6b) - draws - releases."""
    expected = opening + funding + topups - draws - releases
    if not _close(expected, closing):
        raise ReserveRollForwardError(
            f"period {period_index} reserve {reserve_type!r}: roll-forward "
            f"{expected:.6f} != closing {closing:.6f}"
        )


def assert_capital_account(period_index: int, opening: float, contributions: float,
                           distributions: float, ending: float) -> None:
    """opening + contributions - distributions = ending (equity residual)."""
    expected = opening + contributions - distributions
    if not _close(expected, ending):
        raise CapitalAccountError(
            f"period {period_index}: capital account {expected:.6f} != ending {ending:.6f}"
        )

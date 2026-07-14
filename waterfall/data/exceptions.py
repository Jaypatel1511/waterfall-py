"""Typed exception hierarchy for the waterfall engine.

Locked methodology principle: "All assertions raise typed exceptions, never
silently swallow." Every error the engine raises subclasses :class:`WaterfallError`
so a single ``except WaterfallError`` catches the whole family, while callers who
care about a specific failure can catch the narrow type.

Absent *core financials* are represented as ``NaN`` (not ``0.0``) elsewhere in
the engine; these exceptions cover structural/arithmetic failures that must never
be swallowed.
"""


class WaterfallError(Exception):
    """Base class for every error raised by the waterfall engine."""


class InvalidInputError(WaterfallError):
    """A required input is missing, malformed, or fails a documented constraint."""


class UnsupportedFeatureError(WaterfallError):
    """A supplied input requires a feature that is explicitly out of v0.x scope.

    Raised for the methodology's Limitations list (B-piece / A-B mechanics,
    preferred equity, construction-period modeling, sculpted-to-DSCR, defeasance,
    OID, multi-currency, ACT/ACT day-count, tax-credit / SPV-tax modeling, etc.).
    The message names the unsupported feature.
    """


# --- Validation-assertion failures (Validation Tests) ---------------------
class SourceUseImbalanceError(WaterfallError):
    """Source/use tie-out at close failed: sum(sources) != sum(uses)."""


class WaterfallImbalanceError(WaterfallError):
    """Period cash-conservation failed: sum(all sources) != sum(all uses)."""


class PrincipalTraceError(WaterfallError):
    """Per-tranche principal roll-forward did not tie out for a period."""


class InterestReconciliationError(WaterfallError):
    """rate x average balance x day-count fraction != booked period interest."""


class ReserveRollForwardError(WaterfallError):
    """Per-reserve roll-forward (opening + funding - draws - releases) failed."""


class CapitalAccountError(WaterfallError):
    """Equity capital-account roll-forward (opening + contrib - distrib) failed."""


# --- Reserved -------------------------------------------------------------
class ModelConvergenceError(WaterfallError):
    """Reserved: an iterative solve failed to converge (no v0.x solver ships)."""

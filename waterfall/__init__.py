"""waterfall-py: a period-by-period mechanical debt-waterfall engine.

Public API is assembled here. See ``docs/methodology.md`` (the single source of
truth) for the locked modeling decisions this package implements. A byte-identical
copy of that document is bundled in the wheel and located via
:func:`get_methodology_path`.

Dual-import shim (methodology Release Process, WP #6): ``import waterfall_py`` and
``import waterfallpy`` both resolve to this same package (see the top-level
``waterfall_py`` / ``waterfallpy`` shim modules).
"""
from importlib import resources

from waterfall.data import exceptions, schema
from waterfall.data.schema import (
    Deal, Tranche, ReserveConfig, CovenantConfig, Fee, SweepConfig, SweepBand,
)
from waterfall.models.waterfall import run
from waterfall.report.schema import DealResult, PeriodResult
from waterfall.data.exceptions import (
    WaterfallError,
    InvalidInputError,
    UnsupportedFeatureError,
    SourceUseImbalanceError,
    WaterfallImbalanceError,
    PrincipalTraceError,
    InterestReconciliationError,
    ReserveRollForwardError,
    CapitalAccountError,
    ModelConvergenceError,
)

__version__ = "0.1.0"


def get_methodology_path() -> str:
    """Return the filesystem path to the wheel-bundled methodology document.

    Uses :mod:`importlib.resources` so it resolves whether the package is run
    from a source tree or an installed wheel.
    """
    return str(resources.files("waterfall").joinpath("methodology.md"))


__all__ = [
    "__version__",
    "get_methodology_path",
    "run",
    "Deal", "Tranche", "ReserveConfig", "CovenantConfig", "Fee",
    "SweepConfig", "SweepBand", "DealResult", "PeriodResult",
    "exceptions", "schema",
    "WaterfallError",
    "InvalidInputError",
    "UnsupportedFeatureError",
    "SourceUseImbalanceError",
    "WaterfallImbalanceError",
    "PrincipalTraceError",
    "InterestReconciliationError",
    "ReserveRollForwardError",
    "CapitalAccountError",
    "ModelConvergenceError",
]

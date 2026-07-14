"""Covenant metrics and the three-tier cushion.

Every ratio is defined inline by its formula (methodology "Definitional Basis —
No External Authority"). When the relevant denominator is zero (e.g. debt fully
repaid), the covenant is **not tested** and the ratio is ``NaN`` ("n/a") — never
``inf``, ``0``, or a raised error.

Three-tier cushion: performance (minimum) / trap (cash-trap trigger) / default
(acceleration). Coverage metrics (DSCR/LLCR/PLCR/debt-yield/coverage) are
"higher is better" — a value *below* a threshold breaches that tier. Leverage
metrics (LTV, Debt/EBITDA) are "lower is better" — a value *above* a threshold
breaches. A ``None`` threshold means that tier is not configured and is skipped.
"""
import math

from waterfall.data.schema import CovenantConfig

NA = float("nan")

# Metrics where a higher value is stronger (breach below threshold).
_COVERAGE_METRICS = frozenset({
    "DSCR", "LLCR", "PLCR", "debt_yield", "interest_coverage", "fixed_charge",
})
# Metrics where a lower value is stronger (breach above threshold).
_LEVERAGE_METRICS = frozenset({"LTV", "debt_ebitda"})


def _isna(x) -> bool:
    return isinstance(x, float) and math.isnan(x)


# ==========================================================================
# Metric formulas (inline; div-by-zero -> NaN)
# ==========================================================================
def dscr(cfads: float, senior_ds: float, mezz_ds: float = 0.0,
         denominator: str = "senior") -> float:
    """CFADS / scheduled debt service. Denominator scope: 'senior' (default) or 'total'."""
    denom = senior_ds if denominator == "senior" else senior_ds + mezz_ds
    if denom <= 0:
        return NA
    return cfads / denom


def pv(future_cfads, periodic_rate: float) -> float:
    """Present value of ``future_cfads`` (period 1..n) at ``periodic_rate``."""
    return sum(cf / (1 + periodic_rate) ** k for k, cf in enumerate(future_cfads, start=1))


def llcr(future_cfads, senior_balance: float, periodic_senior_cost: float,
         dsra: float = 0.0, include_dsra: bool = False) -> float:
    """PV(CFADS to loan maturity, at senior debt cost) / current senior balance.

    DSRA may be added to the numerator when configured (default off).
    """
    if senior_balance <= 0:
        return NA
    num = pv(future_cfads, periodic_senior_cost) + (dsra if include_dsra else 0.0)
    return num / senior_balance


def plcr(future_cfads, senior_balance: float, periodic_senior_cost: float,
         deal_type: str) -> float:
    """PV(CFADS to project life) / current senior balance — PF only (CRE -> n/a)."""
    if deal_type != "PF":
        return NA
    if senior_balance <= 0:
        return NA
    return pv(future_cfads, periodic_senior_cost) / senior_balance


def ltv(debt_balance: float, asset_value: float) -> float:
    if asset_value <= 0:
        return NA
    return debt_balance / asset_value


def debt_yield(noi: float, debt_balance: float) -> float:
    if debt_balance <= 0:
        return NA
    return noi / debt_balance


def debt_to_ebitda(debt_balance: float, ebitda: float) -> float:
    if ebitda <= 0:
        return NA
    return debt_balance / ebitda


def interest_coverage(cfads: float, interest: float) -> float:
    if interest <= 0:
        return NA
    return cfads / interest


def fixed_charge_coverage(available: float, fixed_charges: float) -> float:
    if fixed_charges <= 0:
        return NA
    return available / fixed_charges


# ==========================================================================
# Three-tier cushion
# ==========================================================================
def evaluate(config: CovenantConfig, value: float) -> str:
    """Classify ``value`` against a covenant's three tiers.

    Returns one of: "n/a" (not tested), "pass", "performance", "trap", "default".
    """
    if _isna(value):
        return "n/a"

    coverage = config.metric in _COVERAGE_METRICS
    # Evaluate most-severe first: default, then trap, then performance.
    for tier, threshold in (("default", config.default),
                            ("trap", config.trap),
                            ("performance", config.performance)):
        if threshold is None:
            continue
        breached = value < threshold if coverage else value > threshold
        if breached:
            return tier
    return "pass"

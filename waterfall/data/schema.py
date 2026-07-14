"""Input contract dataclasses for the waterfall engine.

These carry user-supplied deal terms and validate them at construction. Per the
locked methodology:
- Missing *required* parameters raise :class:`InvalidInputError` (not a bare
  ``TypeError``), so required fields default to ``None`` and are checked here.
- Inputs that require an out-of-scope feature (Limitations list) raise
  :class:`UnsupportedFeatureError`.
- Negative CFADS is valid and passes through (absorbed downstream by the DSRA
  draw); it never raises.

The engine consumes these; it does not verify economic classifications (the
maintenance-vs-growth capex split, required-vs-discretionary reserves) — those
are input-preparer responsibilities per the methodology.
"""
from dataclasses import dataclass, field
from datetime import date
from numbers import Real
from typing import List, Optional

from waterfall.data.exceptions import InvalidInputError, UnsupportedFeatureError
from waterfall.models import dates

# --- Enumerated domains ---------------------------------------------------
TRANCHE_TYPES = ("senior", "mezzanine", "equity")
_OUT_OF_SCOPE_TRANCHES = {
    "b_piece": "B-piece tranche (pulls in A/B note mechanics)",
    "preferred_equity": "preferred equity (quasi-debt promote)",
    "preferred": "preferred equity (quasi-debt promote)",
}
AMORT_TYPES = ("bullet", "fully_amortizing", "balloon", "mortgage", "io", "custom")
_OUT_OF_SCOPE_AMORT = {
    "sculpted": "sculpted amortization (requires an iterative solver)",
    "sculpted_to_dscr": "sculpted-to-DSCR amortization (requires an iterative solver)",
}
RATE_TYPES = ("fixed", "floating", "step_up", "pik")
RESERVE_TYPES = ("DSRA", "IRA", "MRA", "capex", "lease_up", "TI_LC")
COVENANT_METRICS = (
    "DSCR", "LLCR", "PLCR", "LTV", "debt_yield",
    "debt_ebitda", "fixed_charge", "interest_coverage",
)
DSCR_DENOMINATORS = ("senior", "total")
DEAL_TYPES = ("PF", "CRE")
REPORTING_BASES = ("calendar", "fiscal")
_FEE_TYPES = ("arrangement", "commitment", "exit", "prepayment", "agency", "legal")
_OUT_OF_SCOPE_FEES = {"OID": "OID fee (amortizes into yield; needs YTM treatment)"}

# Curated ISO 4217 set (single-currency engine — the value is validated, and a
# tranche in a different currency triggers the multi-currency out-of-scope guard).
ISO_4217 = frozenset({
    "USD", "EUR", "GBP", "JPY", "CHF", "CAD", "AUD", "NZD", "SEK", "NOK", "DKK",
    "CNY", "HKD", "SGD", "INR", "BRL", "MXN", "ZAR", "KRW", "TWD", "THB", "PLN",
    "CZK", "HUF", "ILS", "AED", "SAR", "TRY", "RUB", "IDR", "MYR", "PHP", "CLP",
    "COP", "PEN", "ARS",
})


@dataclass
class Fee:
    """A senior fee / administrative expense (methodology Fee Modeling)."""
    fee_type: str
    amount: float
    period: Optional[int] = None   # None -> recurring each period; else one-off at index

    def __post_init__(self):
        if self.fee_type in _OUT_OF_SCOPE_FEES:
            raise UnsupportedFeatureError(_OUT_OF_SCOPE_FEES[self.fee_type])
        if self.fee_type not in _FEE_TYPES:
            raise InvalidInputError(
                f"unknown fee_type {self.fee_type!r}; supported: {_FEE_TYPES}"
            )
        if not isinstance(self.amount, Real) or self.amount < 0:
            raise InvalidInputError(f"fee amount must be a non-negative number, got {self.amount!r}")


@dataclass
class Tranche:
    """A single tranche in the capital stack (senior / mezzanine / equity)."""
    name: str
    tranche_type: str
    principal: float
    coupon: float = 0.0            # annual rate, e.g. 0.06
    rate_type: str = "fixed"
    day_count: str = dates.ACT_360
    amort_type: str = "bullet"
    term_periods: Optional[int] = None    # periods to maturity (None -> whole horizon)
    amort_periods: Optional[int] = None   # amortization term; > term_periods -> balloon
                                          # at maturity ("30-due-in-10"). None -> term_periods.
    io_periods: int = 0                   # leading interest-only periods
    custom_principal: Optional[List[float]] = None   # per-period scheduled principal
    currency: Optional[str] = None        # None -> deal currency; else multi-currency guard
    is_facility: bool = False             # revolver / delayed-draw (facility draws)
    commitment: Optional[float] = None    # undrawn commitment for facilities
    pik: bool = False

    def __post_init__(self):
        if self.tranche_type in _OUT_OF_SCOPE_TRANCHES:
            raise UnsupportedFeatureError(_OUT_OF_SCOPE_TRANCHES[self.tranche_type])
        if self.tranche_type not in TRANCHE_TYPES:
            raise InvalidInputError(
                f"unknown tranche_type {self.tranche_type!r}; supported: {TRANCHE_TYPES}"
            )
        if self.amort_type in _OUT_OF_SCOPE_AMORT:
            raise UnsupportedFeatureError(_OUT_OF_SCOPE_AMORT[self.amort_type])
        if self.amort_type not in AMORT_TYPES:
            raise InvalidInputError(
                f"unknown amort_type {self.amort_type!r}; supported: {AMORT_TYPES}"
            )
        if self.rate_type not in RATE_TYPES:
            raise InvalidInputError(
                f"unknown rate_type {self.rate_type!r}; supported: {RATE_TYPES}"
            )
        # Day-count domain (ACT/ACT is out of scope). Delegate to dates for a
        # single source of truth on which conventions exist.
        if self.day_count == "ACT/ACT":
            raise UnsupportedFeatureError(
                "ACT/ACT day-count is out of v0.x scope (30/360, ACT/360, ACT/365F only)"
            )
        if self.day_count not in dates._SUPPORTED_DAY_COUNTS:
            raise InvalidInputError(
                f"unknown day_count {self.day_count!r}; supported: {dates._SUPPORTED_DAY_COUNTS}"
            )
        if not isinstance(self.principal, Real) or self.principal < 0:
            raise InvalidInputError(
                f"tranche {self.name!r}: principal must be a non-negative number"
            )
        if self.tranche_type != "equity" and self.principal <= 0:
            raise InvalidInputError(f"tranche {self.name!r}: debt principal must be positive")
        if not (0 <= self.coupon < 1):
            raise InvalidInputError(f"tranche {self.name!r}: coupon must be in [0, 1)")
        if self.currency is not None and self.currency not in ISO_4217:
            raise InvalidInputError(f"tranche {self.name!r}: unknown currency {self.currency!r}")
        if self.term_periods is not None and self.term_periods <= 0:
            raise InvalidInputError(f"tranche {self.name!r}: term_periods must be positive")
        if self.amort_periods is not None and self.amort_periods <= 0:
            raise InvalidInputError(f"tranche {self.name!r}: amort_periods must be positive")
        if self.io_periods < 0:
            raise InvalidInputError(f"tranche {self.name!r}: io_periods must be non-negative")

    @property
    def is_debt(self) -> bool:
        return self.tranche_type in ("senior", "mezzanine")


@dataclass
class ReserveConfig:
    """A reserve account (DSRA/IRA/MRA/capex/lease_up/TI_LC)."""
    reserve_type: str
    required: bool = True
    months_dsra: Optional[int] = None      # DSRA sizing: N months of senior DS
    target_amount: Optional[float] = None  # explicit required balance
    opening_balance: float = 0.0           # pre-funded at close (opening balance at period 0)
    release_period: Optional[int] = None   # user-supplied release trigger (period index)
    lc_funded: bool = False                 # LC alternative -> no cash, "available" for shortfall

    def __post_init__(self):
        if self.reserve_type not in RESERVE_TYPES:
            raise InvalidInputError(
                f"unknown reserve_type {self.reserve_type!r}; supported: {RESERVE_TYPES}"
            )
        if self.opening_balance < 0:
            raise InvalidInputError("reserve opening_balance must be non-negative")
        if self.target_amount is not None and self.target_amount < 0:
            raise InvalidInputError("reserve target_amount must be non-negative")


@dataclass
class CovenantConfig:
    """A covenant with three-tier cushion (performance / trap / default)."""
    metric: str
    performance: Optional[float] = None
    trap: Optional[float] = None
    default: Optional[float] = None
    denominator: str = "senior"      # DSCR denominator scope: senior | total
    test_frequency: str = "A"

    def __post_init__(self):
        if self.metric not in COVENANT_METRICS:
            raise InvalidInputError(
                f"unknown covenant metric {self.metric!r}; supported: {COVENANT_METRICS}"
            )
        if self.denominator not in DSCR_DENOMINATORS:
            raise InvalidInputError(
                f"unknown denominator {self.denominator!r}; supported: {DSCR_DENOMINATORS}"
            )
        if self.test_frequency not in dates._FREQ_MONTHS:
            raise InvalidInputError(
                f"unknown test_frequency {self.test_frequency!r}; supported: {tuple(dates._FREQ_MONTHS)}"
            )


@dataclass
class SweepBand:
    """One leverage band: apply ``sweep_pct`` while leverage <= ``max_leverage``."""
    max_leverage: float
    sweep_pct: float

    def __post_init__(self):
        if not (0 <= self.sweep_pct <= 1):
            raise InvalidInputError("sweep_pct must be in [0, 1]")
        if self.max_leverage < 0:
            raise InvalidInputError("max_leverage must be non-negative")


@dataclass
class SweepConfig:
    """Leverage-banded mandatory ECF sweep configuration."""
    bands: List[SweepBand] = field(default_factory=list)
    default_sweep_pct: float = 0.0   # applied above the highest band

    def __post_init__(self):
        if not (0 <= self.default_sweep_pct <= 1):
            raise InvalidInputError("default_sweep_pct must be in [0, 1]")
        # Ascending by leverage threshold for banded lookup.
        self.bands = sorted(self.bands, key=lambda b: b.max_leverage)


@dataclass
class Deal:
    """Top-level input contract for a mechanical debt-waterfall run."""
    deal_close_date: Optional[date] = None
    operations_start_date: Optional[date] = None
    period_frequency: Optional[str] = None
    tranches: Optional[List[Tranche]] = None
    cfads_stream: Optional[List[float]] = None
    data_currency: Optional[str] = None
    reporting_basis: Optional[str] = None
    deal_type: str = "PF"
    business_day_convention: str = dates.MODIFIED_FOLLOWING
    payment_calendar: str = dates.US_FED
    sofr_calendar: str = dates.SIFMA
    reserves: List[ReserveConfig] = field(default_factory=list)
    covenants: List[CovenantConfig] = field(default_factory=list)
    fees: List[Fee] = field(default_factory=list)
    sweep: Optional[SweepConfig] = None
    project_life_periods: Optional[int] = None       # PF-only, for PLCR horizon
    # Per-period non-CFADS cash flows (each, if given, must match len(cfads_stream)).
    equity_contributions: Optional[List[float]] = None   # cures / equity cash injections
    facility_draws: Optional[List[float]] = None         # revolver / delayed-draw fundings
    event_proceeds: Optional[List[float]] = None         # asset-sale / insurance / issuance
    # Covenant / close inputs.
    asset_value: Optional[float] = None              # for LTV
    project_cost: Optional[float] = None             # uses-of-funds at close (tie-out)
    construction_draw_schedule: Optional[List[float]] = None  # out of scope
    name: str = ""

    def _validate_period_series(self, values, label):
        if values is None:
            return
        if len(values) != self.num_periods:
            raise InvalidInputError(
                f"{label} has length {len(values)}, expected {self.num_periods} "
                "(one per CFADS period)"
            )
        for i, v in enumerate(values):
            if isinstance(v, bool) or not isinstance(v, Real):
                raise InvalidInputError(f"{label}[{i}] must be numeric, got {v!r}")
            if v < 0:
                raise InvalidInputError(f"{label}[{i}] must be non-negative, got {v!r}")

    def __post_init__(self):
        # Out-of-scope construction modeling.
        if self.construction_draw_schedule is not None:
            raise UnsupportedFeatureError(
                "construction-period modeling (draw schedules) is out of v0.x scope; "
                "the engine's clock starts at operations"
            )
        # Required parameters.
        required = {
            "deal_close_date": self.deal_close_date,
            "operations_start_date": self.operations_start_date,
            "period_frequency": self.period_frequency,
            "tranches": self.tranches,
            "cfads_stream": self.cfads_stream,
            "data_currency": self.data_currency,
            "reporting_basis": self.reporting_basis,
        }
        for name, value in required.items():
            if value is None:
                raise InvalidInputError(f"required parameter {name!r} is missing")

        if self.operations_start_date < self.deal_close_date:
            raise InvalidInputError(
                "operations_start_date must be on or after deal_close_date "
                f"({self.operations_start_date} < {self.deal_close_date})"
            )
        if self.period_frequency not in dates._FREQ_MONTHS:
            raise InvalidInputError(
                f"unknown period_frequency {self.period_frequency!r}; "
                f"supported: {tuple(dates._FREQ_MONTHS)}"
            )
        if self.data_currency not in ISO_4217:
            raise InvalidInputError(f"unknown data_currency {self.data_currency!r} (ISO 4217)")
        if self.reporting_basis not in REPORTING_BASES:
            raise InvalidInputError(
                f"unknown reporting_basis {self.reporting_basis!r}; supported: {REPORTING_BASES}"
            )
        if self.deal_type not in DEAL_TYPES:
            raise InvalidInputError(
                f"unknown deal_type {self.deal_type!r}; supported: {DEAL_TYPES}"
            )
        if not self.tranches:
            raise InvalidInputError("deal must have at least one tranche")
        if not any(t.tranche_type == "senior" for t in self.tranches):
            raise InvalidInputError("deal must have at least one senior tranche")
        if not self.cfads_stream:
            raise InvalidInputError("cfads_stream must be a non-empty sequence")
        for i, v in enumerate(self.cfads_stream):
            # Negative CFADS is valid; only non-numeric is rejected.
            if isinstance(v, bool) or not isinstance(v, Real):
                raise InvalidInputError(f"cfads_stream[{i}] must be numeric, got {v!r}")
        # Multi-currency guard: any tranche denominated in a different currency.
        for t in self.tranches:
            if t.currency is not None and t.currency != self.data_currency:
                raise UnsupportedFeatureError(
                    f"multi-currency is out of v0.x scope: tranche {t.name!r} is in "
                    f"{t.currency} but the deal is in {self.data_currency}"
                )
        # Per-period non-CFADS series must align with the CFADS horizon.
        self._validate_period_series(self.equity_contributions, "equity_contributions")
        self._validate_period_series(self.facility_draws, "facility_draws")
        self._validate_period_series(self.event_proceeds, "event_proceeds")
        if self.asset_value is not None and self.asset_value < 0:
            raise InvalidInputError("asset_value must be non-negative")
        if self.project_cost is not None and self.project_cost < 0:
            raise InvalidInputError("project_cost must be non-negative")

    @property
    def num_periods(self) -> int:
        return len(self.cfads_stream)

    @property
    def senior_tranches(self) -> List[Tranche]:
        return [t for t in self.tranches if t.tranche_type == "senior"]

    @property
    def mezz_tranches(self) -> List[Tranche]:
        return [t for t in self.tranches if t.tranche_type == "mezzanine"]

    @property
    def equity_tranches(self) -> List[Tranche]:
        return [t for t in self.tranches if t.tranche_type == "equity"]

    def period_end_dates(self) -> List[date]:
        """Nominal period-end dates for the horizon (one per CFADS period)."""
        horizon = dates._add_months(
            self.operations_start_date,
            self.num_periods * dates._FREQ_MONTHS[self.period_frequency],
        )
        if dates.is_month_end(self.operations_start_date):
            horizon = dates._month_end(horizon)
        ends = dates.generate_period_end_dates(
            self.operations_start_date, horizon, self.period_frequency
        )
        return ends[: self.num_periods]

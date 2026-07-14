"""Day-count, calendars, business-day adjustment, EOM, and period generation.

Locked methodology (Interest Mechanics / Cash Flow dating):
- Day-count v0.x: ``30/360`` (US), ``ACT/360``, ``ACT/365F``. ``ACT/ACT`` is
  explicitly out of scope and raises :class:`UnsupportedFeatureError`.
- Business-day convention: **Modified Following**; period/payment dates on the
  **U.S. Federal Reserve** calendar; SOFR fixings + lookbacks on the **SIFMA U.S.
  Government Securities** calendar. The two calendars are kept distinct; their
  well-known divergence is **Good Friday** (SIFMA closed, Fed open).
- EOM: a month-end origination rolls period-ends to month-end.

Resolved methodology ambiguity (flagged in the build log): EOM ("period-ends on
month-end") and Modified Following ("period/payment dates adjust for business
days") collide when a month-end lands on a weekend/holiday (e.g. 2024-03-31 is a
Sunday). Resolution: :func:`generate_period_end_dates` returns the **nominal
accrual period-end** schedule (EOM-snapped, NOT business-day shifted) — these are
the accrual boundaries used for day-count fractions. :func:`adjust` is the
separate function that derives business-day-adjusted **payment/observation**
dates from any nominal date. This keeps accrual boundaries on true month-ends
while still honoring Modified Following where a settlement date is needed.
"""
import calendar as _calendar
from datetime import date, timedelta

from waterfall.data.exceptions import InvalidInputError, UnsupportedFeatureError

# --- Day-count conventions ------------------------------------------------
THIRTY_360 = "30/360"
ACT_360 = "ACT/360"
ACT_365F = "ACT/365F"
_SUPPORTED_DAY_COUNTS = (THIRTY_360, ACT_360, ACT_365F)
# ACT/ACT deliberately absent — see methodology Limitations.

# --- Calendars ------------------------------------------------------------
US_FED = "US_FED"      # payment / period dates (default)
SIFMA = "SIFMA"        # SOFR fixings + lookbacks
_CALENDARS = (US_FED, SIFMA)

# --- Business-day conventions ---------------------------------------------
UNADJUSTED = "unadjusted"
FOLLOWING = "following"
PRECEDING = "preceding"
MODIFIED_FOLLOWING = "modified_following"
_CONVENTIONS = (UNADJUSTED, FOLLOWING, PRECEDING, MODIFIED_FOLLOWING)

# --- Period frequencies ---------------------------------------------------
_FREQ_MONTHS = {"M": 1, "Q": 3, "SA": 6, "A": 12}


# ==========================================================================
# Day-count
# ==========================================================================
def day_count_fraction(start: date, end: date, convention: str) -> float:
    """Return the year fraction between ``start`` and ``end`` for ``convention``.

    ``ACT/ACT`` raises :class:`UnsupportedFeatureError`; an unknown convention
    raises :class:`InvalidInputError`; ``end < start`` raises
    :class:`InvalidInputError`.
    """
    if convention == "ACT/ACT":
        raise UnsupportedFeatureError(
            "ACT/ACT day-count is out of v0.x scope (30/360, ACT/360, ACT/365F only)"
        )
    if convention not in _SUPPORTED_DAY_COUNTS:
        raise InvalidInputError(
            f"unknown day_count {convention!r}; supported: {_SUPPORTED_DAY_COUNTS}"
        )
    if end < start:
        raise InvalidInputError(f"day_count end {end} precedes start {start}")

    if convention == ACT_360:
        return (end - start).days / 360.0
    if convention == ACT_365F:
        return (end - start).days / 365.0
    # 30/360 US (Bond basis)
    d1, d2 = start.day, end.day
    if d1 == 31:
        d1 = 30
    if d2 == 31 and d1 == 30:
        d2 = 30
    days = 360 * (end.year - start.year) + 30 * (end.month - start.month) + (d2 - d1)
    return days / 360.0


# ==========================================================================
# Calendars
# ==========================================================================
def _nth_weekday(year: int, month: int, weekday: int, n: int) -> date:
    """The ``n``-th ``weekday`` (Mon=0) of ``month`` in ``year``."""
    first = date(year, month, 1)
    offset = (weekday - first.weekday()) % 7
    return first + timedelta(days=offset + 7 * (n - 1))


def _last_weekday(year: int, month: int, weekday: int) -> date:
    last_day = _calendar.monthrange(year, month)[1]
    last = date(year, month, last_day)
    offset = (last.weekday() - weekday) % 7
    return last - timedelta(days=offset)


def _easter(year: int) -> date:
    """Gregorian Easter Sunday (Anonymous Gregorian / computus algorithm)."""
    a = year % 19
    b, c = divmod(year, 100)
    d, e = divmod(b, 4)
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i, k = divmod(c, 4)
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return date(year, month, day)


def _observed(holiday: date):
    """Weekend-observation for a fixed-date holiday.

    Sunday holidays are observed the following Monday. Saturday holidays are not
    a weekday closure (Federal Reserve Banks / SIFMA markets are open the
    preceding Friday), so they yield no observed closure.
    """
    wd = holiday.weekday()
    if wd == 6:      # Sunday -> Monday
        return holiday + timedelta(days=1)
    if wd == 5:      # Saturday -> no weekday closure
        return None
    return holiday


def _federal_holidays(year: int):
    fixed = [date(year, 1, 1), date(year, 7, 4), date(year, 11, 11), date(year, 12, 25)]
    if year >= 2021:
        fixed.append(date(year, 6, 19))  # Juneteenth (federal from 2021)
    floating = [
        _nth_weekday(year, 1, 0, 3),    # MLK — 3rd Mon Jan
        _nth_weekday(year, 2, 0, 3),    # Washington's Birthday — 3rd Mon Feb
        _last_weekday(year, 5, 0),      # Memorial — last Mon May
        _nth_weekday(year, 9, 0, 1),    # Labor — 1st Mon Sep
        _nth_weekday(year, 10, 0, 2),   # Columbus — 2nd Mon Oct
        _nth_weekday(year, 11, 3, 4),   # Thanksgiving — 4th Thu Nov
    ]
    observed = set()
    for h in fixed:
        o = _observed(h)
        if o is not None:
            observed.add(o)
    observed.update(floating)  # floating Monday/Thursday holidays never hit a weekend
    return observed


def _holidays(year: int, cal: str):
    hs = _federal_holidays(year)
    if cal == SIFMA:
        hs = set(hs)
        hs.add(_easter(year) - timedelta(days=2))  # Good Friday
    return hs


def is_business_day(d: date, calendar: str) -> bool:
    """True if ``d`` is a business day on ``calendar`` (US_FED or SIFMA)."""
    if calendar not in _CALENDARS:
        raise InvalidInputError(f"unknown calendar {calendar!r}; supported: {_CALENDARS}")
    if d.weekday() >= 5:
        return False
    return d not in _holidays(d.year, calendar)


# ==========================================================================
# Business-day adjustment
# ==========================================================================
def adjust(d: date, convention: str, calendar: str) -> date:
    """Adjust ``d`` to a business day under ``convention`` on ``calendar``."""
    if convention not in _CONVENTIONS:
        raise InvalidInputError(
            f"unknown business_day_convention {convention!r}; supported: {_CONVENTIONS}"
        )
    if convention == UNADJUSTED:
        return d
    if convention == FOLLOWING:
        return _following(d, calendar)
    if convention == PRECEDING:
        return _preceding(d, calendar)
    # Modified Following
    f = _following(d, calendar)
    if f.month != d.month:
        return _preceding(d, calendar)
    return f


def _following(d: date, calendar: str) -> date:
    while not is_business_day(d, calendar):
        d += timedelta(days=1)
    return d


def _preceding(d: date, calendar: str) -> date:
    while not is_business_day(d, calendar):
        d -= timedelta(days=1)
    return d


# ==========================================================================
# Month-end
# ==========================================================================
def is_month_end(d: date) -> bool:
    return d.day == _calendar.monthrange(d.year, d.month)[1]


def _month_end(d: date) -> date:
    return date(d.year, d.month, _calendar.monthrange(d.year, d.month)[1])


def _add_months(d: date, months: int) -> date:
    m = d.month - 1 + months
    y = d.year + m // 12
    m = m % 12 + 1
    last = _calendar.monthrange(y, m)[1]
    return date(y, m, min(d.day, last))


# ==========================================================================
# Period / stub generation
# ==========================================================================
def generate_period_end_dates(operations_start: date, maturity: date,
                              frequency: str, eom=None):
    """Nominal accrual period-end dates from operations start to maturity.

    Regular period-ends step by ``frequency`` (M/Q/SA/A) from ``operations_start``;
    if ``eom`` (auto-detected from a month-end ``operations_start`` when ``None``)
    they snap to month-end. The final entry is always ``maturity`` — a short stub
    when the last regular period-end falls before it. Dates are **nominal** (not
    business-day adjusted); use :func:`adjust` for payment/observation dates.
    """
    if frequency not in _FREQ_MONTHS:
        raise InvalidInputError(
            f"unknown period_frequency {frequency!r}; supported: {tuple(_FREQ_MONTHS)}"
        )
    if maturity <= operations_start:
        raise InvalidInputError(
            f"maturity {maturity} must be after operations_start {operations_start}"
        )
    if eom is None:
        eom = is_month_end(operations_start)
    step = _FREQ_MONTHS[frequency]

    ends = []
    k = 1
    while True:
        nominal = _add_months(operations_start, k * step)
        if eom:
            nominal = _month_end(nominal)
        if nominal >= maturity:
            break
        ends.append(nominal)
        k += 1
    ends.append(maturity)   # final period-end (stub if shorter than a full period)
    return ends

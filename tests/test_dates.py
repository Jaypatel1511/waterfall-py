"""Dates: day-count, business-day adjustment, calendars, EOM, period/stubs.

Methodology (Interest Mechanics / Cash Flow dating):
- Day-count v0.x: 30/360, ACT/360, ACT/365F. ACT/ACT is out of scope -> raise.
- Business-day convention: Modified Following; period/payment dates on the U.S.
  Federal Reserve calendar; SOFR fixings on the SIFMA U.S. Gov Securities calendar
  (the two calendars are distinct — Good Friday is the well-known divergence).
- EOM: a month-end origination rolls period-ends to month-end; maturity adjusts
  under Modified Following but never rolls into a following month.
- Stubs at operations start and final maturity.
"""
import math
from datetime import date

import pytest

from waterfall.models import dates
from waterfall.data.exceptions import UnsupportedFeatureError, InvalidInputError


# --- Day-count fractions --------------------------------------------------
def test_30_360_half_year():
    assert dates.day_count_fraction(date(2024, 1, 1), date(2024, 7, 1), "30/360") == 0.5


def test_30_360_end_of_month_adjustment():
    # d1=31 -> 30; end d2=29. days = 30*1 + (29-30) = 29.
    dcf = dates.day_count_fraction(date(2024, 1, 31), date(2024, 2, 29), "30/360")
    assert dcf == pytest.approx(29 / 360)


def test_act_360():
    # Jan1->Apr1 2024 = 91 actual days.
    assert dates.day_count_fraction(date(2024, 1, 1), date(2024, 4, 1), "ACT/360") == pytest.approx(91 / 360)


def test_act_365f():
    assert dates.day_count_fraction(date(2024, 1, 1), date(2024, 4, 1), "ACT/365F") == pytest.approx(91 / 365)


def test_act_act_is_out_of_scope():
    with pytest.raises(UnsupportedFeatureError):
        dates.day_count_fraction(date(2024, 1, 1), date(2024, 4, 1), "ACT/ACT")


def test_unknown_day_count_raises_invalid_input():
    with pytest.raises(InvalidInputError):
        dates.day_count_fraction(date(2024, 1, 1), date(2024, 4, 1), "banana")


def test_day_count_end_before_start_raises():
    with pytest.raises(InvalidInputError):
        dates.day_count_fraction(date(2024, 4, 1), date(2024, 1, 1), "ACT/360")


# --- Calendars ------------------------------------------------------------
def test_weekend_is_not_a_business_day_either_calendar():
    sat = date(2024, 6, 29)
    assert not dates.is_business_day(sat, dates.US_FED)
    assert not dates.is_business_day(sat, dates.SIFMA)


def test_christmas_closed_both_calendars():
    xmas = date(2024, 12, 25)
    assert not dates.is_business_day(xmas, dates.US_FED)
    assert not dates.is_business_day(xmas, dates.SIFMA)


def test_good_friday_open_on_fed_closed_on_sifma():
    good_friday_2024 = date(2024, 3, 29)
    assert dates.is_business_day(good_friday_2024, dates.US_FED)
    assert not dates.is_business_day(good_friday_2024, dates.SIFMA)


def test_juneteenth_closed_both():
    juneteenth = date(2024, 6, 19)
    assert not dates.is_business_day(juneteenth, dates.US_FED)
    assert not dates.is_business_day(juneteenth, dates.SIFMA)


def test_new_year_on_sunday_observed_monday():
    # 2023-01-01 is a Sunday -> observed Monday 2023-01-02.
    assert not dates.is_business_day(date(2023, 1, 2), dates.US_FED)


# --- Business-day adjustment ----------------------------------------------
def test_modified_following_rolls_forward_within_month():
    # 2024-03-30 Saturday -> Following = Monday 2024-04-01? that's next month.
    # Use a mid-month weekend instead: 2024-03-16 Sat -> Mon 2024-03-18.
    assert dates.adjust(date(2024, 3, 16), "modified_following", dates.US_FED) == date(2024, 3, 18)


def test_modified_following_rolls_back_when_crossing_month_end():
    # 2024-06-30 is Sunday; Following would be Mon 2024-07-01 (next month) ->
    # Modified Following rolls back to Fri 2024-06-28.
    assert dates.adjust(date(2024, 6, 30), "modified_following", dates.US_FED) == date(2024, 6, 28)


def test_business_day_is_unchanged():
    wed = date(2024, 6, 26)
    assert dates.adjust(wed, "modified_following", dates.US_FED) == wed


# --- EOM ------------------------------------------------------------------
def test_is_month_end():
    assert dates.is_month_end(date(2024, 2, 29))
    assert dates.is_month_end(date(2024, 6, 30))
    assert not dates.is_month_end(date(2024, 6, 29))


# --- Period / stub generation ---------------------------------------------
def test_quarterly_periods_with_final_stub():
    # Operations 2024-01-01, maturity 2024-10-15, quarterly.
    # Regular quarter-ends 04-01, 07-01, 10-01, then a short final stub to 10-15.
    ends = dates.generate_period_end_dates(
        operations_start=date(2024, 1, 1),
        maturity=date(2024, 10, 15),
        frequency="Q",
    )
    assert ends[-1] == date(2024, 10, 15)   # final stub lands on maturity
    assert date(2024, 4, 1) in ends
    assert ends == sorted(ends)
    # No period-end past maturity.
    assert all(d <= date(2024, 10, 15) for d in ends)


def test_eom_origination_rolls_period_ends_to_month_end():
    # Month-end operations start -> monthly period ends stay on month-end.
    ends = dates.generate_period_end_dates(
        operations_start=date(2024, 1, 31),
        maturity=date(2024, 4, 30),
        frequency="M",
    )
    assert date(2024, 2, 29) in ends   # not 2024-02-31/03-02
    assert date(2024, 3, 31) in ends
    assert ends[-1] == date(2024, 4, 30)


def test_unknown_frequency_raises():
    with pytest.raises(InvalidInputError):
        dates.generate_period_end_dates(date(2024, 1, 1), date(2024, 12, 31), "weekly")

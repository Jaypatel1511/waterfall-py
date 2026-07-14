"""Typed exception hierarchy — the engine never silently swallows.

Methodology: "All assertions raise typed exceptions, never silently swallow."
Every specific error must subclass WaterfallError so a caller can catch the
whole family with one `except WaterfallError`.
"""
import pytest

from waterfall.data.exceptions import (
    WaterfallError,
    InvalidInputError,
    SourceUseImbalanceError,
    WaterfallImbalanceError,
    ReserveRollForwardError,
    PrincipalTraceError,
    InterestReconciliationError,
    CapitalAccountError,
    UnsupportedFeatureError,
    ModelConvergenceError,
)

ALL_SUBCLASSES = [
    InvalidInputError,
    SourceUseImbalanceError,
    WaterfallImbalanceError,
    ReserveRollForwardError,
    PrincipalTraceError,
    InterestReconciliationError,
    CapitalAccountError,
    UnsupportedFeatureError,
    ModelConvergenceError,
]


@pytest.mark.parametrize("exc", ALL_SUBCLASSES)
def test_every_typed_error_subclasses_waterfall_error(exc):
    assert issubclass(exc, WaterfallError)


@pytest.mark.parametrize("exc", ALL_SUBCLASSES)
def test_typed_errors_are_catchable_as_base(exc):
    with pytest.raises(WaterfallError):
        raise exc("boom")


def test_base_is_an_exception():
    assert issubclass(WaterfallError, Exception)


def test_unsupported_feature_carries_feature_name():
    err = UnsupportedFeatureError("B-piece tranche")
    assert "B-piece" in str(err)

"""Each of the six assertions must fire on a deliberately corrupted input.

These prove the assertions actually assert (not just exist). Balanced inputs must
pass silently.
"""
import pytest

from waterfall.audit import assertions as asrt
from waterfall.audit.log import PeriodLedger
from waterfall.data.exceptions import (
    SourceUseImbalanceError, WaterfallImbalanceError, PrincipalTraceError,
    InterestReconciliationError, ReserveRollForwardError, CapitalAccountError,
)


def test_cash_conservation_fires_on_imbalanced_ledger():
    led = PeriodLedger(0)
    led.add_source("cfads", 100.0)
    led.add_use("senior_interest", 90.0)   # 10 unaccounted
    with pytest.raises(WaterfallImbalanceError):
        asrt.assert_cash_conservation(led)


def test_cash_conservation_passes_when_balanced():
    led = PeriodLedger(0)
    led.add_source("cfads", 100.0)
    led.add_use("senior_interest", 60.0)
    led.add_use("equity_distribution", 40.0)
    asrt.assert_cash_conservation(led)   # no raise


def test_source_use_close_fires():
    with pytest.raises(SourceUseImbalanceError):
        asrt.assert_source_use_close(sources=1_000_000.0, uses=999_000.0)


def test_principal_trace_fires():
    with pytest.raises(PrincipalTraceError):
        # opening 1,000,000 + draws 0 - scheduled 100,000 - prepay 0 - sweep 0 = 900,000
        asrt.assert_principal_trace("Term A", 0, opening=1_000_000.0, draws=0.0,
                                    scheduled=100_000.0, prepayments=0.0, sweeps=0.0,
                                    closing=850_000.0)   # wrong closing


def test_principal_trace_passes_when_consistent():
    asrt.assert_principal_trace("Term A", 0, opening=1_000_000.0, draws=200_000.0,
                                scheduled=100_000.0, prepayments=50_000.0, sweeps=30_000.0,
                                closing=1_020_000.0)


def test_interest_reconciliation_fires():
    with pytest.raises(InterestReconciliationError):
        asrt.assert_interest_reconciliation("Term A", 0, coupon=0.06,
                                            avg_balance=1_000_000.0, dcf=0.25,
                                            booked_interest=20_000.0)   # should be 15,000


def test_reserve_roll_forward_fires():
    with pytest.raises(ReserveRollForwardError):
        # opening 100k + funding 50k + topup 0 - draws 20k - releases 0 = 130k
        asrt.assert_reserve_roll_forward("DSRA", 0, opening=100_000.0, funding=50_000.0,
                                         topups=0.0, draws=20_000.0, releases=0.0,
                                         closing=120_000.0)   # wrong


def test_reserve_roll_forward_counts_the_step6b_topup_term():
    # A valid roll-forward with a NONZERO step-6b top-up must pass; dropping the
    # ``+ topups`` term from the assertion would make this fire (audit M1 probe).
    asrt.assert_reserve_roll_forward("capex", 0, opening=100_000.0, funding=0.0,
                                     topups=90_000.0, draws=0.0, releases=0.0,
                                     closing=190_000.0)
    with pytest.raises(ReserveRollForwardError):
        asrt.assert_reserve_roll_forward("capex", 0, opening=100_000.0, funding=0.0,
                                         topups=90_000.0, draws=0.0, releases=0.0,
                                         closing=100_000.0)   # ignores the top-up


def test_capital_account_fires():
    with pytest.raises(CapitalAccountError):
        asrt.assert_capital_account(0, opening=3_000_000.0, contributions=100_000.0,
                                    distributions=200_000.0, ending=3_000_000.0)   # wrong

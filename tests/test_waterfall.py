import pytest
import pandas as pd
from waterfall.models.waterfall import run


def test_waterfall_runs(sample_deal):
    result = run(sample_deal)
    assert result is not None
    assert len(result.period_results) == 5


def test_total_interest_positive(sample_deal):
    result = run(sample_deal)
    assert result.total_interest_paid > 0


def test_total_principal_positive(sample_deal):
    result = run(sample_deal)
    assert result.total_principal_paid > 0


def test_equity_distributions_non_negative(sample_deal):
    result = run(sample_deal)
    assert result.total_equity_distributions >= 0


def test_summary_returns_dataframe(sample_deal):
    result = run(sample_deal)
    df = result.summary()
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 5


def test_dscr_table_returns_dataframe(sample_deal):
    result = run(sample_deal)
    df = result.dscr_table()
    assert isinstance(df, pd.DataFrame)


def test_to_dict_keys(sample_deal):
    result = run(sample_deal)
    d = result.to_dict()
    assert "total_equity_distributions" in d
    assert "num_covenant_breaches" in d
    assert "num_defaults" in d


def test_no_defaults_on_healthy_deal(sample_deal):
    result = run(sample_deal)
    assert result.num_defaults == 0


def test_covenant_breach_on_stressed_deal(
        senior_tranche, mezz_tranche, equity_tranche):
    from waterfall.data.schema import CashFlowPeriod, DealStructure
    stressed_flows = [
        CashFlowPeriod(period=i, cfads=500_000)
        for i in range(1, 4)
    ]
    deal = DealStructure(
        name="Stressed Deal",
        tranches=[senior_tranche, mezz_tranche, equity_tranche],
        cash_flows=stressed_flows,
        min_dscr=1.25,
    )
    result = run(deal)
    assert result.num_covenant_breaches > 0

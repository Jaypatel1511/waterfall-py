import pytest
from waterfall.models.dscr import calculate, summary_table


def test_dscr_calculation():
    result = calculate(1, cfads=1_200_000, total_debt_service=800_000, min_dscr=1.25)
    assert result.dscr == pytest.approx(1.5)


def test_dscr_covenant_breach():
    result = calculate(1, cfads=900_000, total_debt_service=800_000, min_dscr=1.25)
    assert result.covenant_breach is True
    assert result.status == "LOCK-UP"


def test_dscr_default():
    result = calculate(1, cfads=500_000, total_debt_service=800_000, min_dscr=1.25)
    assert result.default is True
    assert result.status == "DEFAULT"


def test_dscr_ok():
    result = calculate(1, cfads=1_500_000, total_debt_service=800_000, min_dscr=1.25)
    assert result.covenant_breach is False
    assert result.status == "OK"


def test_dscr_no_debt_service():
    result = calculate(1, cfads=1_000_000, total_debt_service=0, min_dscr=1.25)
    assert result.dscr == float("inf")


def test_summary_table_returns_dataframe():
    import pandas as pd
    results = [
        calculate(i, cfads=1_200_000, total_debt_service=800_000, min_dscr=1.25)
        for i in range(1, 4)
    ]
    df = summary_table(results)
    assert isinstance(df, pd.DataFrame)
    assert len(df) == 3

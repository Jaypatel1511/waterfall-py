import pytest
from waterfall.data.schema import Tranche, CashFlowPeriod, DealStructure


@pytest.fixture
def senior_tranche():
    return Tranche(
        name="Senior Debt",
        principal=7_000_000,
        rate=0.06,
        term_years=10,
        priority=1,
    )


@pytest.fixture
def mezz_tranche():
    return Tranche(
        name="Mezzanine",
        principal=2_000_000,
        rate=0.12,
        term_years=10,
        priority=2,
        is_mezz=True,
    )


@pytest.fixture
def equity_tranche():
    return Tranche(
        name="Equity",
        principal=1_000_000,
        rate=0.0,
        term_years=10,
        priority=3,
        is_equity=True,
    )


@pytest.fixture
def sample_cash_flows():
    return [
        CashFlowPeriod(period=i, cfads=1_200_000, operating_expenses=50_000)
        for i in range(1, 6)
    ]


@pytest.fixture
def sample_deal(senior_tranche, mezz_tranche, equity_tranche, sample_cash_flows):
    return DealStructure(
        name="Midtown Mixed-Use Project",
        tranches=[senior_tranche, mezz_tranche, equity_tranche],
        cash_flows=sample_cash_flows,
        min_dscr=1.25,
        dsra_months=6,
        cash_sweep_pct=1.0,
    )

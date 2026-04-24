from dataclasses import dataclass
import pandas as pd

from waterfall.data.schema import DealStructure
from waterfall.models.tranches import build_states
from waterfall.models import dscr as dscr_module
from waterfall.models import sweep as sweep_module


@dataclass
class PeriodResult:
    """Results for a single period in the waterfall."""
    period: int
    cfads: float
    operating_expenses: float
    senior_interest_paid: float
    senior_principal_paid: float
    mezz_interest_paid: float
    mezz_principal_paid: float
    dsra_funding: float
    sweep_result: object
    dscr_result: object
    equity_distribution: float
    cash_shortfall: float


@dataclass
class WaterfallResult:
    """Full waterfall output across all periods."""
    deal_name: str
    period_results: list
    tranche_states: list
    total_equity_distributions: float
    total_interest_paid: float
    total_principal_paid: float
    num_covenant_breaches: int
    num_defaults: int

    def summary(self) -> pd.DataFrame:
        rows = []
        for r in self.period_results:
            rows.append({
                "Period": r.period,
                "CFADS ($)": f"${r.cfads:,.0f}",
                "Sr Interest ($)": f"${r.senior_interest_paid:,.0f}",
                "Sr Principal ($)": f"${r.senior_principal_paid:,.0f}",
                "Mezz Interest ($)": f"${r.mezz_interest_paid:,.0f}",
                "Mezz Principal ($)": f"${r.mezz_principal_paid:,.0f}",
                "Equity Dist ($)": f"${r.equity_distribution:,.0f}",
                "DSCR": f"{r.dscr_result.dscr:.2f}x"
                        if r.dscr_result.dscr != float('inf') else "N/A",
                "Status": r.dscr_result.status,
            })

        df = pd.DataFrame(rows)
        print(f"\nWaterfall Summary — {self.deal_name}")
        print("=" * 95)
        print(df.to_string(index=False))
        print("=" * 95)
        print(f"  Total Interest Paid:      ${self.total_interest_paid:,.0f}")
        print(f"  Total Principal Paid:     ${self.total_principal_paid:,.0f}")
        print(f"  Total Equity Distributions: ${self.total_equity_distributions:,.0f}")
        print(f"  Covenant Breaches:        {self.num_covenant_breaches}")
        print(f"  Defaults:                 {self.num_defaults}")
        print()
        return df

    def dscr_table(self) -> pd.DataFrame:
        return dscr_module.summary_table(
            [r.dscr_result for r in self.period_results]
        )

    def to_dict(self) -> dict:
        return {
            "deal_name": self.deal_name,
            "total_equity_distributions": self.total_equity_distributions,
            "total_interest_paid": self.total_interest_paid,
            "total_principal_paid": self.total_principal_paid,
            "num_covenant_breaches": self.num_covenant_breaches,
            "num_defaults": self.num_defaults,
        }


def run(deal: DealStructure) -> WaterfallResult:
    """
    Run the full cash flow waterfall across all periods.

    Waterfall priority each period:
    1. Operating expenses
    2. Senior interest
    3. Senior principal (scheduled)
    4. DSRA funding
    5. Mezz interest
    6. Mezz principal (scheduled)
    7. Cash sweep (excess to senior, then mezz)
    8. Equity distribution (if DSCR covenant met)

    Args:
        deal: DealStructure with tranches and cash flow periods

    Returns:
        WaterfallResult with period-by-period breakdown
    """
    states = build_states(deal.tranches)
    senior_states = [s for s in states if not s.tranche.is_mezz
                     and not s.tranche.is_equity]
    mezz_states = [s for s in states if s.tranche.is_mezz]

    period_results = []
    dsra_balance = 0.0

    for cf in deal.cash_flows:
        cash = cf.cfads
        period = cf.period

        # 1. Operating expenses
        op_ex = min(cf.operating_expenses, cash)
        cash -= op_ex

        # 2 & 3. Senior interest + principal
        sr_interest = 0.0
        sr_principal = 0.0
        sr_shortfall = 0.0

        for state in senior_states:
            paid, cash, shortfall = state.pay_interest(cash)
            sr_interest += paid
            sr_shortfall += shortfall

        for state in senior_states:
            paid, cash, shortfall = state.pay_principal(cash)
            sr_principal += paid
            sr_shortfall += shortfall

        total_senior_ds = sr_interest + sr_principal

        # 4. DSRA funding — target 6 months of senior debt service
        monthly_ds = total_senior_ds / 12
        dsra_target = monthly_ds * deal.dsra_months
        dsra_contribution = min(max(dsra_target - dsra_balance, 0), cash)
        dsra_balance += dsra_contribution
        cash -= dsra_contribution

        # 5 & 6. Mezz interest + principal
        mezz_interest = 0.0
        mezz_principal = 0.0

        for state in mezz_states:
            state.accrue_pik()
            paid, cash, _ = state.pay_interest(cash)
            mezz_interest += paid

        for state in mezz_states:
            paid, cash, _ = state.pay_principal(cash)
            mezz_principal += paid

        total_ds = total_senior_ds + mezz_interest + mezz_principal

        # DSCR calculation
        dscr_result = dscr_module.calculate(
            period=period,
            cfads=cf.cfads,
            total_debt_service=total_ds,
            min_dscr=deal.min_dscr,
        )

        # 7 & 8. Cash sweep + equity distribution
        sweep_result = sweep_module.apply(
            period=period,
            available_cash=cash,
            senior_states=senior_states,
            mezz_states=mezz_states,
            cash_sweep_pct=deal.cash_sweep_pct,
            dscr_lock_up=dscr_result.lock_up,
        )

        period_results.append(PeriodResult(
            period=period,
            cfads=cf.cfads,
            operating_expenses=op_ex,
            senior_interest_paid=sr_interest,
            senior_principal_paid=sr_principal,
            mezz_interest_paid=mezz_interest,
            mezz_principal_paid=mezz_principal,
            dsra_funding=dsra_contribution,
            sweep_result=sweep_result,
            dscr_result=dscr_result,
            equity_distribution=sweep_result.equity_distribution,
            cash_shortfall=sr_shortfall,
        ))

    return WaterfallResult(
        deal_name=deal.name,
        period_results=period_results,
        tranche_states=states,
        total_equity_distributions=sum(
            r.equity_distribution for r in period_results),
        total_interest_paid=sum(
            r.senior_interest_paid + r.mezz_interest_paid
            for r in period_results),
        total_principal_paid=sum(
            r.senior_principal_paid + r.mezz_principal_paid
            for r in period_results),
        num_covenant_breaches=sum(
            1 for r in period_results if r.dscr_result.covenant_breach),
        num_defaults=sum(
            1 for r in period_results if r.dscr_result.default),
    )

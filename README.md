# waterfall-py 💧

**Python debt waterfall engine for structured finance.**

Model multi-tranche capital stacks — senior debt, mezzanine, and equity — with
period-by-period cash distribution, DSCR tracking, covenant breach detection,
and cash sweep logic.

---

## Why waterfall-py?

Every structured finance, real estate, and private credit deal has a cash flow
waterfall — but every analyst builds it from scratch in Excel. waterfall-py
standardizes the engine so you can focus on the deal, not the model.

---

## Installation

    pip install waterfall-py

---

## Quickstart

    from waterfall import Tranche, CashFlowPeriod, DealStructure, run

    senior = Tranche(name="Senior Debt", principal=7_000_000,
                     rate=0.06, term_years=10, priority=1)

    mezz = Tranche(name="Mezzanine", principal=2_000_000,
                   rate=0.12, term_years=10, priority=2, is_mezz=True)

    equity = Tranche(name="Equity", principal=1_000_000,
                     rate=0.0, term_years=10, priority=3, is_equity=True)

    cash_flows = [
        CashFlowPeriod(period=i, cfads=1_200_000, operating_expenses=50_000)
        for i in range(1, 11)
    ]

    deal = DealStructure(
        name="Midtown Mixed-Use Project",
        tranches=[senior, mezz, equity],
        cash_flows=cash_flows,
        min_dscr=1.25,
        dsra_months=6,
        cash_sweep_pct=1.0,
    )

    result = run(deal)
    result.summary()
    result.dscr_table()

---

## Waterfall Priority

    1. Operating expenses
    2. Senior interest
    3. Senior principal (scheduled amortization)
    4. DSRA funding (target: N months of debt service)
    5. Mezzanine interest
    6. Mezzanine principal
    7. Cash sweep (excess cash prepays senior, then mezz)
    8. Equity distribution (only if DSCR covenant is met)

---

## Modules

- tranches  - Tranche mechanics: interest accrual, principal payments, sweep
- dscr      - DSCR calculation and covenant tracking per period
- sweep     - Cash sweep and equity distribution logic
- waterfall - Full period-by-period distribution engine

---

## DSCR Covenant Logic

- DSCR above min       - OK, equity distributions permitted
- DSCR below min_dscr  - LOCK-UP, equity distributions blocked
- DSCR below 1.0       - DEFAULT, debt service cannot be fully covered

---

## Running Tests

    PYTHONPATH=. pytest tests/ -v

28 tests across all modules.

---

## Who This Is For

- Private credit analysts modeling leveraged deals
- Real estate finance teams structuring debt stacks
- Project finance practitioners building waterfall models
- Anyone replacing a bespoke Excel waterfall with auditable Python

---

## License

MIT 2026 Jaypatel1511

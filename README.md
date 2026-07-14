# waterfall-py 💧

**Period-by-period mechanical debt-waterfall engine for structured finance.**

waterfall-py runs a mechanical, auditable cash-flow waterfall over a
user-supplied CFADS stream and a capital stack of senior + mezzanine + residual
equity. It is a **tight core**: it computes what the deal terms and the CFADS
imply, period by period, and proves the arithmetic with built-in validation
assertions. It does **not** project cash flows, make credit judgments, or model
anything on the Limitations list.

> **Mechanical waterfall computation only. Not a credit recommendation. CFADS
> inputs are user-supplied projections, not modeled cash flows.**

The single source of truth for every modeling decision is
[`docs/methodology.md`](docs/methodology.md), a copy of which is bundled in the
wheel and locatable via `waterfall.get_methodology_path()`.

---

## Installation

    pip install waterfall-py

Both `import waterfall_py` and `import waterfallpy` resolve to the same package
as `import waterfall`.

---

## Quickstart

```python
from datetime import date
from waterfall import run, Deal, Tranche, ReserveConfig, CovenantConfig, SweepConfig, SweepBand

senior = Tranche(name="Term A", tranche_type="senior", principal=10_000_000,
                 coupon=0.06, day_count="ACT/360", amort_type="fully_amortizing",
                 term_periods=8)
mezz = Tranche(name="Mezz", tranche_type="mezzanine", principal=2_000_000,
               coupon=0.10, amort_type="bullet", term_periods=8)
equity = Tranche(name="Sponsor Equity", tranche_type="equity", principal=3_000_000)

deal = Deal(
    deal_close_date=date(2024, 1, 1),
    operations_start_date=date(2024, 1, 1),
    period_frequency="Q",                       # M / Q / SA / A
    deal_type="PF",                             # PF or CRE
    tranches=[senior, mezz, equity],
    cfads_stream=[1_400_000] * 8,               # one operating CFADS per period
    data_currency="USD",
    reporting_basis="calendar",
    reserves=[ReserveConfig(reserve_type="DSRA", months_dsra=6, opening_balance=750_000)],
    covenants=[CovenantConfig(metric="DSCR", trap=1.10, default=1.00)],
    sweep=SweepConfig(bands=[SweepBand(4.0, 1.0), SweepBand(3.0, 0.5)]),
)

result = run(deal)

from waterfall.report import export
df = export.to_period_dataframe(result)   # native DataFrame
print(export.render_text(result))         # text report (opens with the disclaimer)
export.to_excel(result, "deal.xlsx")      # openpyxl workbook
```

---

## Waterfall Priority (LOCKED)

Each operating period, operating cash (CFADS) — supplemented at the steps they
fund by non-CFADS sources — is applied in one acyclic priority order:

    1. Senior fees & administrative expenses
    2. Senior debt service (interest, then scheduled principal, pari-passu pro-rata)
       shortfall covered by: DSRA draw, then equity cash-injection cure
    3. Required reserve funding / replenishment (DSRA to required, then others)
    4. Mezzanine debt service
    5. Mandatory ECF sweep — ECF ≡ cash remaining after steps 1–4; leverage-banded;
       forced to 100% under a cash-trap
    6. Permitted junior uses from retained ECF (6a capex / 6b top-ups / 6c distributions)
    7. Residual to equity (absent an active cash-trap)

Reserve releases and event proceeds are applied on a **separate proceeds path**
(to outstanding debt in priority, then equity — the equity leg gated under a
cash-trap while debt remains). CFADS stays operating-only; every non-CFADS source
is recorded separately.

---

## Built-in validation assertions (primary defensibility)

Every period, the engine asserts — raising a typed exception on any failure:

- **Source/use tie-out at close** — sources = uses
- **Period cash-conservation** — Σ all modeled sources = Σ all modeled uses (enumerated from the per-period ledger)
- **Principal trace** — opening + facility draws − scheduled amort − prepayments − sweeps = closing, per tranche
- **Interest reconciliation** — rate × average balance × day-count fraction = period interest
- **Reserve roll-forward** — closing = opening + funding + top-ups − draws − releases, per reserve
- **Capital-account roll-forward** — opening + contributions − distributions = ending

---

## Covenants

DSCR, LLCR, PLCR (PF only), LTV, debt yield, Debt/EBITDA, fixed-charge and
interest coverage are defined inline by formula. A zero denominator (e.g. debt
fully repaid) reports **n/a** — never ∞, 0, or a raised error. Each covenant
carries a three-tier cushion: performance / trap / default. Every breach flag is
labeled a *mechanical test result computed by the engine from user-supplied CFADS
and the deal terms* — never a legal conclusion.

---

## Out of scope (raise `UnsupportedFeatureError`)

B-piece / A-B mechanics, preferred equity, construction-period modeling,
sculpted-to-DSCR amortization, defeasance, OID, multi-currency, ACT/ACT
day-count, tax-credit / SPV-tax modeling, and NOI/CFADS projection. See the
Limitations section of the methodology.

---

## Running tests

    PYTHONPATH=. pytest tests/ -v

---

## License

MIT — Jaypatel1511

# waterfall-py: Methodology

> **STATUS: SKELETON / DECISIONS PENDING.** This document captures the design decisions that govern what waterfall-py computes and what it explicitly refuses to compute. Decisions must be made and reviewed for citations, gaps, and contradictions BEFORE writing the analysis code (working principle #1). Each section below identifies the decision(s) that need to be locked.

## Scope

**In scope.**
- Real estate debt waterfalls: CRE acquisition, bridge, construction, permanent, refinance. Property types: multifamily, office, industrial, retail, hospitality, mixed-use.
- Project finance debt waterfalls: infrastructure, renewables (wind/solar/storage), PPP/P3, mining, oil & gas. SPV-based, limited-recourse.
- Period-by-period mechanical cash flow computation given a CFADS stream and a capital stack.

**Out of scope (explicitly stated, refuse on input).**
- Tax credit equity waterfalls (LIHTC, NMTC, HTC, ITC partnership flips). Capital account maintenance, DRO/QIO, HLBV, recapture — not this tool. Use a separate tax-credit-equity tool.
- CMBS bond-level tranching (AAA/AA/A/.../unrated). This tool models loan-level waterfalls, not bond-pool waterfalls.
- Derivatives accounting and hedge effectiveness (ASC 815). Floating-rate inputs are modeled at the index reset; hedge cash flows are inputs, not modeled.
- NOI projection (CRE) and construction draw schedules. These are inputs to the engine, not outputs of it. Composing with separate projection tools is expected.
- Credit judgment. Output is mechanical waterfall computation. Never produces "investable," "approvable," or "creditworthy" claims.

## Capital Stack Architecture

**DECISIONS TO LOCK:**
- Supported tranche types: senior secured (Term A, Term B, revolver, delayed-draw, accordion), mezzanine, B-piece, preferred equity (treated as quasi-debt with stated yield), common equity (residual).
- Seniority handling: strict priority queue vs. pari-passu rings vs. configurable. Recommend: configurable priority with pari-passu groups, allocating within a group pro-rata by current balance.
- Intercreditor assumptions: standstill periods, payment blockage rights, purchase options. Recommend: default ICA assumptions documented per tranche type, overrideable.
- Multi-currency: in or out? Recommend: out for v0.x. Single-currency only, with currency code in metadata for downstream consumers.

## Interest Mechanics

**DECISIONS TO LOCK:**
- Rate types supported: fixed, floating (index + spread, with caps/floors), step-up, PIK (toggle per period), default rate accrual.
- Floating-rate indices: SOFR, Term SOFR (1M/3M/6M), SOFR-OIS, EURIBOR (if multi-currency added later). Index reset schedule (in advance vs. arrears, lookback days).
- Day-count conventions: 30/360, ACT/360, ACT/365, ACT/ACT. Default per tranche-type convention (CRE senior usually ACT/360, project finance usually ACT/360 for US bank loans — confirm).
- Accrual vs. payment timing: accrue daily, pay periodically. Stub periods at close and final maturity computed pro-rata.
- PIK behavior: capitalize to principal at end of period, or accrue and pay at maturity? Recommend: configurable per tranche; default to capitalize end-of-period.

## Principal Amortization

**DECISIONS TO LOCK:**
- Schedule types: bullet, fully-amortizing, balloon (partial amort then balloon at maturity), mortgage-style (constant payment with longer amort period than term — "30-due-in-10"), interest-only periods, sculpted (project-finance back-loaded), custom (user-supplied schedule).
- Amortization basis: straight-line, mortgage-constant, sculpted-to-DSCR (project finance technique that sets amort to maintain target DSCR). Recommend: support all three, default per tranche type.
- Recompute behavior on prepayment: re-amortize remaining balance over remaining term, or maintain payment and shorten term? Recommend: configurable; default re-amortize.

## Fee Modeling

**DECISIONS TO LOCK:**
- Fee types: arrangement (upfront, % of commitment), commitment/unused-line (periodic, % of undrawn), exit (% of repaid balance at maturity or prepayment), prepayment penalty (declining schedule or make-whole), agency, legal-cost passthrough.
- Treatment: cash outflows on the closing/payment date; do not netted against interest. Show separately in waterfall output.
- Accrual basis for periodic fees: same day-count as the tranche or fee-specific?

## Reserves

**DECISIONS TO LOCK:**
- Reserve types: DSRA (debt service reserve account), IRA (interest reserve, common in construction/bridge), MRA (maintenance reserve, project finance), capex reserve, lease-up reserve, tenant improvement / leasing commission reserve.
- Sizing rules: N months of debt service (DSRA), N months of interest (IRA), % of revenue (MRA), schedule-based (capex), trigger-based (lease-up). Each reserve has its own funding and release rules.
- Funding priority: pre-funded at close vs. funded from operations vs. hybrid. Document the default for each reserve type.
- Release rules: at maturity (DSRA), on trigger event (IRA released when stabilization achieved), per schedule (capex).
- LC alternative: support letter-of-credit substitution for DSRA? Recommend: model as a flag (lc_funded=True means no cash reserve, but reserve "available" for shortfall purposes).

## Covenant Pack

**DECISIONS TO LOCK:**
- Ratios supported: DSCR (backward-looking trailing, forward-looking projected, average vs. minimum), LTV, debt yield, LLCR (loan life coverage ratio — project finance), PLCR (project life coverage ratio), Debt/EBITDA, fixed charge coverage, interest coverage.
- Testing frequency: quarterly / semi-annually / annually, with annual averages for some ratios. Configurable per covenant.
- Covenant types: maintenance (tested every period) vs. springing (only tested on action like incurrence) vs. incurrence-only.
- Cushion levels: minimum levels (default), trigger levels (cash trap, sweep activation), default levels (acceleration). Recommend: three-tier model — performance / trap / default.
- Breach consequences: lock-up (no equity distributions), cash trap (sweep activated), springing covenant activation, event of default. Configurable.

## Cash Sweep Mechanics

**DECISIONS TO LOCK:**
- Sweep types: mandatory (excess cash flow above thresholds), discretionary (borrower election), event-triggered (covenant breach activates).
- Leverage-banded step-downs: 100% sweep above X leverage, 75% between X and Y, 50% between Y and Z, 0% below Z. Bands configurable per deal.
- ECF (excess cash flow) definition: standard LSTA-style — CFADS minus debt service minus permitted distributions minus permitted capex minus reserve funding. Document the formula.
- Exclusions from sweep: permitted acquisitions, permitted distributions below leverage threshold, working capital fluctuations. Configurable.
- Sweep application order: senior pro-rata vs. last-out first vs. configurable.

## Cure Rights

**DECISIONS TO LOCK:**
- Equity cure mechanics: deemed EBITDA boost vs. cash injection for debt service.
- Caps: size cap per cure ($X or % of EBITDA), frequency cap (N cures per 12 months / over loan life), max consecutive cures.
- Overcure: do excess cure proceeds count against next period's covenant or get returned? Configurable.
- Mulligan: one-time waiver right per loan? In or out? Recommend: model as a configurable flag, default off.

## Mandatory Prepayments

**DECISIONS TO LOCK:**
- Triggers: ECF sweep (covered above), asset sale proceeds, insurance/condemnation proceeds, debt incurrence, change of control, equity issuance.
- Reinvestment rights: window to reinvest proceeds before sweep applies (typical 12–18 months). Configurable per trigger.
- Application order: senior pro-rata to scheduled amort, then to next maturity, then to revolver. Configurable.
- Premium on mandatory prepayment: typically no premium (vs. optional prepayment which may carry call protection). Confirm.

## Default and Remedies

**DECISIONS TO LOCK:**
- Default categories: payment default, covenant default, cross-default, bankruptcy, judgment.
- Grace periods: typical 5 business days payment, 30 days covenant, 0 days bankruptcy. Configurable.
- Post-default interest: default rate spread (typically +2.00% over stated rate). Configurable.
- Acceleration: optional on covenant default, automatic on bankruptcy. Document the behavior.
- Intercreditor standstill: senior gets N days/months of exclusive enforcement before mezz can act. Default per ICA conventions.

## Call Protection

**DECISIONS TO LOCK:**
- Non-call period: hard NC for N years from close.
- Declining call schedule: e.g., NC-2, 102, 101, par. Configurable per tranche.
- Make-whole computation: T+50, T+25, fixed spread to comparable treasury. Document the discount rate and computation.
- Yield maintenance vs. defeasance: which to support? Recommend: yield maintenance only in v0.x; defeasance is a CMBS-specific complexity that can be deferred.
- Par-call windows: typical last 3–6 months at par before maturity. Configurable.

## Cash Flow Source Assumptions

**DECISIONS TO LOCK:**
- CFADS is an INPUT, not computed by this tool. The engine consumes a period-by-period CFADS stream (or CFADS-equivalent for project finance: revenues minus opex minus tax minus maintenance capex).
- Construction draw schedules: inputs only. No construction-period modeling beyond accepting a draw schedule and computing interest reserve drawdown.
- NOI projection (CRE): out of scope. Compose with a separate projection tool.
- Stress scenarios: the engine should accept a list of CFADS streams (base, downside, severe) and run the waterfall on each. Stress generation itself is not the engine's job.

## Required vs. Optional Parameters

**DECISIONS TO LOCK:**
- Required (no default, raise InvalidInputError on omission): deal_close_date, period_frequency (M/Q/SA/A), tranches list, cfads_stream.
- Required with validation: data_currency (ISO 4217), reporting_basis (calendar / fiscal).
- Optional with documented defaults: day_count (per tranche-type default), reserve sizing (per reserve-type default), covenant levels (none by default — explicit only).
- All optional defaults documented inline in code AND in methodology.md (single source of truth).

## Validation Tests (Built-In)

**DECISIONS TO LOCK:**
- Source/use tie-out at close: sum of sources = sum of uses, raise SourceUseImbalanceError if mismatch above tolerance.
- Principal trace: opening balance + draws – scheduled amort – prepayments – sweeps = closing balance per tranche per period. Assert at every period.
- Interest accrual reconciliation: rate × average balance × day-count fraction = period interest, within tolerance.
- DSCR audit table: shows CFADS, debt service, DSCR per period, with arithmetic auditable.
- Capital account roll-forward (equity residual): contributions – distributions = ending balance.
- All assertions raise typed exceptions, never silently swallow. Pattern matches fair-lending-screener `InsufficientDataError`-style.

## Output Schema

**DECISIONS TO LOCK:**
- Primary outputs: period table (DataFrame), tranche-level summary, covenant status table, source/use statement, audit log.
- Period table columns: period_index, period_end_date, cfads, debt_service_by_tranche, principal_by_tranche, interest_by_tranche, reserves, sweep_amount, equity_distribution, covenant_status, dscr.
- Audit log: every decision the engine makes per period (sweep triggered, covenant breached, cure applied) with rationale.
- Export formats: native DataFrame, Excel via openpyxl (with formatted columns), JSON for API consumers.

## Language Guardrails (Strictly Enforced)

**DECISIONS TO LOCK:**
- Output never produces credit judgments. No "investable," "approvable," "creditworthy," "recommended."
- Output never produces forward-looking statements not grounded in input. If CFADS is provided as projection, output explicitly labels results as projections.
- Standard disclaimer: "Mechanical waterfall computation only. Not a credit recommendation. CFADS inputs are user-supplied projections, not modeled cash flows."
- Pattern matches fair-lending-screener language guardrails — three-location enforcement (report rendering, DealResult.limitations, DealResult.interpretation if added) with through-function regression test.

## Limitations (Documented in 3+ Places: methodology.md, DealResult.limitations, every report, _limitations_doc.md)

- No NOI / CFADS projection modeling
- No construction risk or completion guarantee modeling
- No tax modeling (corporate, withholding, partnership)
- No derivatives / hedge accounting
- No equity promote / carried interest (this is a debt waterfall — equity is residual only)
- No CMBS bond-level tranching
- No tax credit equity flips
- Single-currency only

## Citations (To Verify)

- LSTA (Loan Syndications and Trading Association) — Model Credit Agreement Provisions, ECF definitions, cure rights
- ULI / NAIOP — CRE underwriting standards
- MBA Commercial/Multifamily Mortgage Origination data conventions
- World Bank PPP Reference Guide — project finance debt sizing and DSCR conventions
- S&P Global Ratings: Project Finance Framework — LLCR/PLCR computation

## Release Process

**DECISIONS TO LOCK:**
- CI-driven publish per working principle #8 — release.yml with verify-version → build → test-wheel → publish pipeline.
- OIDC Trusted Publisher (when ready to publish). PyPI Trusted Publisher must be configured BEFORE first CI publish.
- Version-guard via tomllib, Python 3.11+ in publish step.
- All actions SHA-pinned.
- Dual-import shim from day 1: `waterfall_py` and `waterfallpy` both resolve to the same package (working principle #6).
- CHANGELOG from day 1 (working principle #7).
- Methodology doc bundled in wheel via importlib.resources (pattern from fair-lending-screener v0.2.0).

## Audit Discipline (For Reference)

This tool sits in a defensible-output category: a counterparty's lawyer might read its output in litigation over a deal. Apply the fair-lending-screener audit pattern:
- Self-audit before publish (working principle #3)
- Hostile second-pass audit in fresh session (working principle #4)
- Through-function regression tests for every guardrail
- No "this test exists" assumption — verify the test actually runs and asserts on the right thing

---

**Next steps:**
1. Review this skeleton, mark decisions to lock vs. defer.
2. For locked decisions, draft the rationale and citation per section (fair-lending-screener `03_*.md` is the template for what "locked" looks like).
3. THEN scope v0.x feature set against the locked decisions.
4. THEN write code against the locked methodology.

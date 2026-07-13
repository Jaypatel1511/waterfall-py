# waterfall-py: Methodology

> **STATUS: DECISIONS LOCKED — PENDING FRESH RE-AUDIT.** This document captures the design decisions that govern what waterfall-py computes and what it explicitly refuses to compute. The methodology skeleton (commit 53294fc) was hostile-audited (`methodology_audit.md`, `methodology-audit` branch: 2 CRIT / 5 HIGH / 6 MED / 5 LOW). CRIT-1, CRIT-2, HIGH-3, HIGH-5 were resolved mechanically in commit f87f689. This revision resolves the remaining HIGH, MEDIUM, and LOW findings and locks the v0.x scope. Per working principle #1, this resolved methodology must pass a fresh-session hostile re-audit (0 CRIT/HIGH) BEFORE any analysis code is written.

## v0.x Scope Posture

waterfall-py v0.x is a **tight core**: a period-by-period mechanical debt-waterfall engine over a user-supplied CFADS stream and a capital stack of senior + mezzanine + residual equity. Ambitious skeleton features that add audit surface without serving the core are **explicitly scoped out of v0.x** (enumerated in Limitations) and revisited only after the core ships and settles (depth-over-breadth). Every "locked" decision below states the v0.x default and, where relevant, what is deferred.

## Scope

**In scope.**
- Real estate debt waterfalls: CRE acquisition, bridge, permanent, refinance. Property types: multifamily, office, industrial, retail, hospitality, mixed-use.
- Project finance debt waterfalls: infrastructure, renewables (wind/solar/storage), PPP/P3, mining, oil & gas. SPV-based, limited-recourse.
- Period-by-period mechanical cash flow computation given a CFADS stream and a capital stack.

**Out of scope (explicitly stated, refuse on input).**
- Tax credit equity waterfalls (LIHTC, NMTC, HTC, ITC partnership flips). Capital account maintenance, DRO/QIO, HLBV, recapture — not this tool. Use a separate tax-credit-equity tool.
- **SPV tax distribution provisions** (phantom-income distributions to equity holders to cover tax on pass-through income in excess of distributions). These are SPV operating provisions, not tax-credit equity, but they are out of v0.x scope. If needed, they are treated as user-specified distribution inputs, not modeled. *(Resolves MED-1.)*
- CMBS bond-level tranching (AAA/AA/A/.../unrated). This tool models loan-level waterfalls, not bond-pool waterfalls.
- **A/B note structures.** B-piece is not a supported tranche type in v0.x. A/B-specific mechanics — interest-shortfall absorption (B before A), appraisal reduction amounts (ARA), sequential-vs-pro-rata loss allocation — are out of scope. The standard seniority queue must not be used to approximate an A/B deal. *(Resolves MED-3.)*
- Construction-period modeling. Construction draw schedules are inputs only; the engine does not compute construction-period balances or interest-reserve drawdown during construction (see Reserves / MED-2 resolution).
- Derivatives accounting and hedge effectiveness (ASC 815). Floating-rate inputs are modeled at the index reset; hedge cash flows are inputs, not modeled.
- NOI projection (CRE) and CFADS projection. These are inputs to the engine, not outputs of it. Composing with separate projection tools is expected.
- Credit judgment. Output is mechanical waterfall computation. Never produces "investable," "approvable," or "creditworthy" claims. Covenant-breach outputs are labeled as mechanical test results (see Language Guardrails / HIGH-2).

## Capital Stack Architecture — LOCKED

- **Supported tranche types (v0.x):** senior secured facilities (Term A, Term B, revolver, delayed-draw, accordion), mezzanine, common equity (residual). **Deferred:** B-piece, preferred equity (quasi-debt with stated yield). Rationale: B-piece pulls in A/B mechanics (out of scope, MED-3); preferred-equity promote/quasi-debt mechanics widen the surface without serving the core debt waterfall.
- **Seniority handling:** configurable priority queue with pari-passu groups; within a group, allocate pro-rata by current balance. (Verified CLEAN-equivalent market convention.)
- **Intercreditor assumptions:** default ICA assumptions documented per tranche type (standstill periods, payment-blockage rights), overrideable. Purchase options deferred.
- **Multi-currency:** OUT for v0.x. Single-currency only; currency code carried in metadata for downstream consumers.

## Interest Mechanics — LOCKED

- **Rate types:** fixed, floating (index + spread, with caps/floors), step-up, PIK (toggle per period), default-rate accrual.
- **Floating-rate indices:** SOFR, Term SOFR (1M/3M/6M). EURIBOR/other deferred with multi-currency. Index reset default **in advance**; lookback days configurable.
- **Day-count conventions (v0.x):** 30/360, ACT/360, ACT/365 (Fixed). **ACT/ACT is dropped from v0.x** — it is rare in loan computations and its ISDA/ICMA/AFB variants diverge on leap-year treatment; ACT/365(Fixed) covers the use cases. If ACT/ACT is ever added, the ISDA variant must be named explicitly. *(Resolves LOW-4.)*
- **Day-count default:** ACT/360 for US commercial bank loans — both CRE senior and US project-finance bank debt. (30/360 is a residential-mortgage / bond convention and is not the project-finance default.) *(HIGH-3, already applied in f87f689; retained here.)*
- **Business-day convention (LOCKED):** **Modified Following** is the v0.x default. **Holiday calendar:** **U.S. Federal Reserve** calendar is the v0.x default. A period-end date landing on a weekend or U.S. bank holiday is adjusted under Modified Following; grace periods stated in "business days" resolve against this calendar. Multi-currency / multi-calendar support is deferred with multi-currency. *(Resolves HIGH-4.)*
- **Accrual vs. payment timing:** accrue daily, pay periodically. Stub periods at close and final maturity computed pro-rata over the actual (calendar-adjusted) day count.
- **PIK behavior:** configurable per tranche; default **capitalize to principal at end of period**.

## Principal Amortization — LOCKED

- **Schedule types (v0.x):** bullet, fully-amortizing, balloon (partial amort then balloon), mortgage-style ("30-due-in-10": constant payment on a longer amort period than term), interest-only periods, custom (user-supplied schedule). **Deferred:** sculpted (project-finance back-loaded, sculpted-to-DSCR) — it requires an iterative solver (the approach whose bogus Greene citation was removed in CRIT-1) and is deferred to a later version; when built, the numerical solve (Newton-Raphson / goal-seek) is documented inline in code, not against an econometrics citation.
- **Amortization basis:** straight-line, mortgage-constant. Sculpted-to-DSCR deferred (see above).
- **Recompute behavior on prepayment:** configurable; default **re-amortize** remaining balance over remaining term.

## Fee Modeling — LOCKED

- **Fee types (v0.x):** arrangement (upfront, % of commitment), commitment/unused-line (periodic, % of undrawn), exit (% of repaid balance), prepayment penalty (declining schedule or make-whole), agency, legal-cost passthrough. **Deferred:** Original Issue Discount (OID). OID amortizes over loan life into yield and requires yield-to-maturity treatment distinct from cash fees; it is out of v0.x scope. All v0.x fees are treated as cash outflows on their funding/payment date. *(Resolves LOW-5.)*
- **Treatment:** cash outflows on the closing/payment date; not netted against interest. Shown separately in waterfall output.
- **Accrual basis for periodic fees:** same day-count as the tranche unless a fee-specific basis is supplied.

## Reserves — LOCKED

- **Reserve types:** DSRA (debt service reserve), IRA (interest reserve), MRA (maintenance reserve), capex reserve, lease-up reserve, TI/LC reserve.
- **IRA scope (LOCKED):** IRA is **funded at close and released on a stabilization trigger**. The engine does **not** compute construction-period IRA drawdown — that would be construction-period modeling, which is out of scope. Draw schedules remain inputs-only. This removes the skeleton's scope contradiction (Scope said construction is inputs-only; Reserves implied the engine draws the IRA down over construction). *(Resolves MED-2.)*
- **Sizing rules:** N months of debt service (DSRA), N months of interest (IRA), % of revenue (MRA), schedule-based (capex), trigger-based (lease-up). Each reserve has its own funding and release rules, documented per type.
- **Funding priority:** pre-funded at close vs. funded from operations vs. hybrid — default documented per reserve type.
- **Release rules:** DSRA at maturity; IRA on stabilization trigger; capex per schedule.
- **LC alternative:** `lc_funded=True` flag — no cash reserve, but reserve treated as "available" for shortfall purposes.

## Covenant Pack — LOCKED

- **Ratios:** DSCR (trailing / forward-looking, average vs. minimum), LTV, debt yield, LLCR (loan-life coverage), PLCR (project-life coverage), Debt/EBITDA, fixed-charge coverage, interest coverage.
- **Testing frequency:** quarterly / semi-annual / annual, with annual averages where applicable. Configurable per covenant.
- **Covenant types:** maintenance (tested every period), springing (tested on action), incurrence-only.
- **Cushion levels — three-tier:** performance (minimum), trap (trigger — cash trap / sweep activation), default (acceleration). Configurable.
- **Breach consequences:** lock-up (no equity distributions), cash trap (sweep activated), springing activation, event of default. Configurable.
- **Breach-output labeling (LOCKED, HIGH-2):** Every covenant-breach signal, cash-trap activation, and event-of-default computation is labeled **"mechanical test result based on user-supplied inputs."** The standard disclaimer appears **adjacent to every breach flag in the output**, not only in summary headers. Breach outputs are numeric test results, not credit determinations, and the output must make that explicit at the point of each flag. *(Resolves HIGH-2.)*

## Cash Sweep Mechanics — LOCKED

- **Sweep types:** mandatory (excess cash flow above thresholds), discretionary (borrower election), event-triggered (covenant breach activates).
- **Leverage-banded step-downs:** e.g., 100% sweep above X leverage, 75% between X and Y, 50% between Y and Z, 0% below Z. Bands configurable per deal. (Verified CLEAN.)
- **ECF (excess cash flow) definition — LOCKED (HIGH-1):** single formula —
  **ECF = CFADS − debt service − permitted distributions − permitted capex (growth/discretionary only) − reserve funding.**
  "Permitted capex" in this formula means **growth/discretionary capex only**. The CFADS input is defined (see Cash Flow Source Assumptions) as already net of **maintenance capex**; the ECF formula must **not** deduct maintenance capex a second time. The input preparer is responsible for supplying CFADS net of maintenance capex and for classifying only growth/discretionary capex into the ECF deduction. This single formula serves both CRE and project-finance contexts without double-counting. *(Resolves HIGH-1.)*
- **Exclusions from sweep:** permitted acquisitions, permitted distributions below leverage threshold, working-capital fluctuations. Configurable.
- **Sweep application order:** configurable (senior pro-rata / last-out-first).

## Cure Rights — LOCKED

- **Equity cure mechanics:** deemed EBITDA boost vs. cash injection for debt service (configurable). (Verified CLEAN.)
- **Caps:** size cap per cure ($X or % of EBITDA), frequency cap (N cures per 12 months / over loan life), max consecutive cures.
- **Overcure:** configurable — excess cure proceeds count against next period's covenant or are returned.
- **Mulligan:** configurable flag, default **off**.

## Mandatory Prepayments — LOCKED

- **Triggers:** ECF sweep (above), asset-sale proceeds, insurance/condemnation proceeds, debt incurrence, change of control, equity issuance.
- **Reinvestment rights:** window to reinvest proceeds before sweep applies (typical 12–18 months). Configurable per trigger.
- **Application order:** senior pro-rata to scheduled amort, then next maturity, then revolver. Configurable.
- **Premium:** mandatory prepayments carry **no premium** by default (optional prepayments may carry call protection — see Call Protection).

## Default and Remedies — LOCKED

- **Default categories:** payment, covenant, cross-default, bankruptcy, judgment.
- **Grace periods (default, configurable):** payment 5 business days, covenant 30 days, bankruptcy 0 days. "Business days" resolve against the U.S. Federal Reserve calendar under Modified Following (HIGH-4).
- **Post-default interest:** default-rate spread, default **+2.00%** over stated rate, configurable.
- **Acceleration:** optional on covenant default, automatic on bankruptcy.
- **Intercreditor standstill:** senior gets N days/months of exclusive enforcement before mezz can act; default per ICA conventions.

## Call Protection — LOCKED

- **Non-call period:** hard NC for N years from close (configurable).
- **Declining call schedule:** e.g., NC-2, 102, 101, par (configurable per tranche).
- **Make-whole computation:** discount of remaining scheduled cash flows to a comparable-treasury reference. **Spread levels are configurable with no default** — T+50 / T+25 are market approximations, not published conventions, and are not hard-coded as defaults; they vary by credit, vintage, and lender. The discount-rate construction and computation are documented; the spread is a required input when make-whole is used. *(Resolves LOW-1.)*
- **Yield maintenance vs. defeasance:** **yield maintenance only in v0.x.** Defeasance (CMBS-specific) deferred.
- **Par-call windows:** typical last 3–6 months at par before maturity, configurable.

## Cash Flow Source Assumptions — LOCKED

- **CFADS is an INPUT**, not computed by this tool. The engine consumes a period-by-period CFADS stream. For project finance, CFADS = revenues − opex − tax − **maintenance capex** (maintenance capex is netted here, which is why the ECF formula deducts growth/discretionary capex only — see HIGH-1).
- **CFADS sign convention (LOCKED, MED-5):** positive CFADS = **cash available for debt service** (inflow). 
- **Period dating (LOCKED, MED-5):** cash flows are dated at **period end**. LLCR/PLCR and DSCR computations assume period-end CFADS. (Mid-period dating deferred; if added, it becomes an explicit configurable convention.)
- **Negative CFADS handling (LOCKED, MED-5):** negative CFADS is **passed through as-is** so the debt-service-coverage/shortfall computation surfaces the shortfall. The engine does **not** raise an error on negative CFADS (stress scenarios routinely produce it).
- **Construction draw schedules:** inputs only. No construction-period modeling (consistent with MED-2).
- **Stress scenarios:** the engine accepts a list of CFADS streams (base, downside, severe) and runs the waterfall on each. Stress generation itself is not the engine's job.

## Required vs. Optional Parameters — LOCKED

- **Required (raise `InvalidInputError` on omission):** `deal_close_date`, `period_frequency` (M/Q/SA/A), `tranches` list, `cfads_stream`.
- **Required with validation:** `data_currency` (ISO 4217), `reporting_basis` (calendar / fiscal).
- **Optional with documented defaults:** `day_count` (per tranche-type default), `business_day_convention` (default Modified Following), `holiday_calendar` (default U.S. Federal Reserve), reserve sizing (per reserve-type default), covenant levels (none by default — explicit only).
- All optional defaults documented inline in code AND in this methodology (single source of truth).

## Validation Tests (Built-In) — LOCKED

These audit assertions are the **primary defensibility mechanism for numeric output** (see MED-6 resolution in Language Guardrails). They are not optional niceties:

- **Source/use tie-out at close:** sum of sources = sum of uses; raise `SourceUseImbalanceError` if mismatch above tolerance.
- **Principal trace:** opening balance + draws − scheduled amort − prepayments − sweeps = closing balance, per tranche per period. Asserted every period.
- **Interest accrual reconciliation:** rate × average balance × day-count fraction = period interest, within tolerance.
- **DSCR audit table:** CFADS, debt service, DSCR per period, arithmetic auditable.
- **Capital account roll-forward (equity residual):** contributions − distributions = ending balance.
- All assertions raise typed exceptions, never silently swallow (matches fair-lending-screener `InsufficientDataError`-style hierarchy).

## Output Schema — LOCKED

- **Primary outputs:** period table (DataFrame), tranche-level summary, covenant status table, source/use statement, audit log.
- **Period table columns:** `period_index`, `period_end_date`, `cfads`, `debt_service_by_tranche`, `principal_by_tranche`, `interest_by_tranche`, `reserves`, `sweep_amount`, `equity_distribution`, `covenant_status`, `dscr`.
- **Audit log:** every decision the engine makes per period (sweep triggered, covenant breached, cure applied) with rationale and the "mechanical test result" label on breach entries.
- **Export formats:** native DataFrame, Excel via openpyxl (formatted), JSON for API consumers.

## Language Guardrails (Strictly Enforced) — LOCKED

- Output never produces credit judgments. No "investable," "approvable," "creditworthy," "recommended."
- Output never produces forward-looking statements not grounded in input. If CFADS is a projection, output labels results as projections.
- **Standard disclaimer:** "Mechanical waterfall computation only. Not a credit recommendation. CFADS inputs are user-supplied projections, not modeled cash flows."
- **Two-layer defensibility (LOCKED, HIGH-2 + MED-6):**
  1. **Language layer** — the three-location disclaimer pattern from fair-lending-screener (report rendering, `DealResult.limitations`, `DealResult.interpretation` if added) with a through-function regression test. This protects against the "no credit judgment" language risk. Additionally, per HIGH-2, breach signals carry the "mechanical test result based on user-supplied inputs" label **adjacent to each flag**.
  2. **Numeric layer (primary)** — the audit-assertion pattern (Validation Tests) is the primary defensibility mechanism for numeric output misuse: the principal trace, interest-accrual reconciliation, source/use tie-out, and the period-by-period audit log let a reviewer verify the numbers are internally correct. A disclaimer does not make a wrong number defensible; the audit trail does. The disclaimer and the audit trail are complementary, not substitutes. *(Resolves MED-6.)*

## Limitations (Documented in 3+ Places: methodology.md, DealResult.limitations, every report, _limitations_doc.md) — LOCKED

- No NOI / CFADS projection modeling
- No construction-period modeling (draw schedules and IRA drawdown during construction are out of scope; IRA is funded at close and released on stabilization)
- No tax modeling (corporate, withholding, partnership); no SPV tax-distribution provisions
- No derivatives / hedge accounting
- No equity promote / carried interest (this is a debt waterfall — equity is residual only)
- No CMBS bond-level tranching
- No A/B note structures or B-piece shortfall mechanics
- No preferred-equity / quasi-debt tranche
- No tax credit equity flips
- No defeasance (yield maintenance only)
- No OID modeling (all fees are cash outflows on funding date)
- No sculpted-to-DSCR amortization (deferred — requires iterative solver)
- No ACT/ACT day-count (30/360, ACT/360, ACT/365F only)
- Single-currency only

## Citations — RESOLVED / VERIFY-AT-RE-AUDIT

Citation discipline (learned from CRIT-2 / HIGH-5): **never cite a bond/pool-level source for loan-level behavior**, and pin every citation to an edition/section. Any citation not yet pinned is marked VERIFY-NEEDED and must be resolved (pinned or dropped) at the re-audit before code.

- **LSTA (Loan Syndications and Trading Association) — Model Credit Agreement Provisions (MCAP), June 2025 edition** — ECF definitions, cure rights. *(Pins LOW-3; the June 2025 edition was the most recent as of the audit — confirm edition/section at re-audit.)*
- **S&P Global Ratings — Project Finance Framework** — LLCR/PLCR and DSCR sizing conventions (loan-level, project-finance). Primary source for DSCR conventions, replacing the World Bank PPP Reference Guide as the DSCR authority. *(Resolves MED-4: World Bank PPP Guide is a procurement/policy document, not a lender-practice DSCR source; dropped as the DSCR authority. Confirm S&P PF criteria section at re-audit.)*
- **MBA (Mortgage Bankers Association) Commercial/Multifamily origination conventions** — CRE underwriting-standards reference, replacing ULI/NAIOP for underwriting conventions. ULI/NAIOP are best-practice/research bodies, not primary underwriting authorities; cite them only for property-type data if used, never for underwriting conventions. *(Resolves LOW-2.)*
- **REMOVED in f87f689 (do not reintroduce):** Greene §17.x (wrong — Ch. 17 is discrete choice, not numerical methods; and an econometrics text has no PF sculpted-amort content), "SIFMA CMBS Investor Reporting Package" (misattributed — the IRP is CREFC, not SIFMA; and it is a reporting standard, not a covenant-testing methodology), Moody's CMBS Surveillance criteria (bond/pool-level, not loan-level covenant testing). *(CRIT-1, CRIT-2, HIGH-5.)*

## Release Process — LOCKED

- CI-driven publish (working principle #8): `release.yml` with verify-version → build → test-wheel → publish pipeline.
- OIDC Trusted Publisher configured BEFORE first CI publish. No local-tree publishes.
- Version-guard via tomllib, Python 3.11+ in publish step. All actions SHA-pinned.
- Dual-import shim from day 1: `waterfall_py` and `waterfallpy` both resolve to the same package (working principle #6).
- CHANGELOG from day 1 (working principle #7).
- Methodology doc bundled in wheel via importlib.resources (pattern from fair-lending-screener v0.2.0).

## Audit Discipline (For Reference)

This tool sits in a defensible-output category: a counterparty's lawyer might read its output in litigation over a deal. Apply the fair-lending-screener audit pattern:
- Self-audit before publish (working principle #3)
- Hostile second-pass audit in a fresh session (working principle #4) — **this resolved methodology must pass a 0-CRIT/0-HIGH re-audit before code is written**
- Through-function regression tests for every guardrail
- No "this test exists" assumption — verify the test actually runs and asserts on the right thing

---

**Next steps:**
1. Fresh-session hostile re-audit of THIS resolved methodology (must confirm 0 CRIT / 0 HIGH; verify the two VERIFY-NEEDED citations are pinned or dropped).
2. On re-audit GO, scope the v0.x feature set into a build plan against the locked decisions.
3. THEN write code against the locked methodology (negative-case-first tests, principal-trace / audit-assertion discipline).

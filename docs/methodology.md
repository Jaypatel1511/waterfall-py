# waterfall-py: Methodology

> **STATUS: DECISIONS LOCKED (PASS-3 RESOLVED) — PENDING FRESH RE-AUDIT #3.** Lineage: skeleton (53294fc) → first hostile audit `methodology_audit.md` (2 CRIT / 5 HIGH / 6 MED / 5 LOW) → mechanical fixes f87f689 (CRIT-1/2, HIGH-3/5) → first resolution 9875f44 → **second hostile audit `methodology_audit_pass2.md` (methodology-review-pass2, ffb2af9): NO-GO, 2 CRIT / 4 HIGH / 6 MED / 4 LOW** → pass-2 resolution → **third hostile audit `methodology_audit_pass3.md` (methodology-review-pass3, a28168c): NO-GO, 1 CRIT / 0 HIGH / 5 MED / 6 LOW** → this revision. Pass-2 removed the authority-per-mechanic approach and defines every computed metric inline by formula. The pass-3 CRITICAL was self-inflicted: the pass-2 fix for the ECF double-count netted required reserve funding *into* the CFADS definition, which ranks reserves above debt service (backwards) and manufactures false covenant breaches. This revision **removes that term from CFADS** (CFADS is again cash available for debt service, net of maintenance capex only), moves required reserve funding to an explicit waterfall step below debt service, and states a single ordered waterfall. Per working principle #1, this resolved methodology must pass a fresh-session hostile re-audit (0 CRIT / 0 HIGH) BEFORE any analysis code is written.

## v0.x Scope Posture

waterfall-py v0.x is a **tight core**: a period-by-period mechanical debt-waterfall engine over a user-supplied CFADS stream and a capital stack of senior + mezzanine + residual equity. Ambitious skeleton features that add audit surface without serving the core are **explicitly scoped out** (enumerated in Limitations) and revisited only after the core ships and settles (depth-over-breadth).

**Modeling horizon (LOCKED — resolves pass-2 construction seam).** The engine models the **operating period only**. Period 0 is the **conversion / stabilization date**. Construction periods are not modeled: no construction-period balances, no interest accrual before period 0, no covenant testing before period 0. Reserves funded at close (DSRA, IRA) appear as **opening reserve balances at period 0**, not as construction-period drawdowns. This removes the collision between accrue-from-close, IRA-funded-at-close, and construction being out of scope that produced spurious defaults every construction period.

## Scope

**In scope.**
- Real estate debt waterfalls: CRE acquisition, bridge, permanent, refinance (operating period). Property types: multifamily, office, industrial, retail, hospitality, mixed-use.
- Project finance debt waterfalls (operating period): infrastructure, renewables (wind/solar/storage), PPP/P3, mining, oil & gas. SPV-based, limited-recourse.
- Period-by-period mechanical cash flow computation given a CFADS stream and a capital stack, starting at operations.

**Out of scope (explicitly stated, refuse on input).**
- Tax credit equity waterfalls (LIHTC, NMTC, HTC, ITC partnership flips). Capital account maintenance, DRO/QIO, HLBV, recapture — not this tool.
- **SPV tax distribution provisions** (phantom-income distributions to equity). Out of v0.x scope. If supplied as distribution inputs, they are treated as **permitted distributions that sit ahead of a covenant lock-up** (tax distributions are customarily carved out of lock-up restrictions); the engine does not model the phantom-income calculation. *(Resolves MED-1 + pass-2 tax-distribution/lock-up interaction.)*
- CMBS bond-level tranching. Loan-level waterfalls only.
- **A/B note structures / B-piece shortfall mechanics** (ARA, sequential-vs-pro-rata loss allocation, B-before-A shortfall absorption). The standard seniority queue must not approximate an A/B deal. *(MED-3.)*
- **Construction-period modeling.** Draw schedules are inputs to the projection that produces CFADS; the engine's clock starts at operations (see Modeling horizon).
- Derivatives accounting / hedge effectiveness (ASC 815). Floating-rate inputs modeled at index reset; hedge cash flows are inputs.
- NOI / CFADS projection. Inputs to the engine, not outputs. Compose with a separate projection tool.
- Credit judgment. Output is mechanical computation; covenant-breach outputs are mechanical test results, never credit determinations (see Language Guardrails).

## Capital Stack Architecture — LOCKED

- **Supported tranche types (v0.x):** senior secured facilities (Term A, Term B, revolver, delayed-draw, accordion), mezzanine, common equity (residual). **Deferred:** B-piece (pulls in A/B mechanics), preferred equity (quasi-debt promote widens surface without serving the core).
- **Seniority handling:** configurable priority queue with pari-passu groups; within a group, allocate pro-rata by current balance.
- **Intercreditor assumptions:** default ICA assumptions per tranche type (standstill periods, payment-blockage rights), overrideable. Purchase options deferred.
- **Multi-currency:** OUT for v0.x. Single-currency; currency code in metadata.

## Interest Mechanics — LOCKED

- **Rate types:** fixed, floating (index + spread, caps/floors), step-up, PIK (toggle per period), default-rate accrual.
- **Floating indices:** SOFR, Term SOFR (1M/3M/6M). Reset default **in advance**; lookback days configurable. EURIBOR/other deferred with multi-currency.
- **Day-count (v0.x):** 30/360, ACT/360, ACT/365 (Fixed). **ACT/ACT dropped** — rare in loans; ISDA/ICMA/AFB variants diverge on leap years; ACT/365F covers the cases. *(LOW-4.)*
- **Day-count default:** ACT/360 for US commercial bank loans — CRE senior and US project-finance bank debt alike. *(HIGH-3.)*
- **Business-day convention (LOCKED):** **Modified Following**, default holiday calendar **U.S. Federal Reserve**. Applies to period-end and payment dates.
- **Month-end (EOM) rule (LOCKED — pass-2 seam):** a loan originated on a month-end rolls all period-end dates to month-end (EOM convention on). Maturity dates adjust under Modified Following but never roll into a following month.
- **SOFR fixing calendar (LOCKED — pass-2 seam):** SOFR/Term SOFR observations and fixings use the **SIFMA U.S. Government Securities Business Day calendar**, which is distinct from the U.S. Federal Reserve payment calendar. The engine keeps the two calendars separate: rate fixings **and their lookback/observation periods** on the SIFMA calendar, payment/period dates on the Fed calendar. Every computed date is assigned to exactly one calendar (pass-3 MED).
- **Accrual vs. payment:** accrue daily, pay periodically; **accrual begins at `operations_start_date` (period 0), not at `deal_close_date`** (operations-only horizon — pass-3 MED). Stub periods are computed at operations start and at final maturity, pro-rata over the calendar-adjusted day count. `deal_close_date` is used only for the source/use tie-out at close, not for accrual.
- **PIK behavior:** configurable per tranche; default **capitalize to principal at end of period**.

## Principal Amortization — LOCKED

- **Schedule types (v0.x):** bullet, fully-amortizing, balloon, mortgage-style ("30-due-in-10"), interest-only periods, custom (user-supplied). **Deferred:** sculpted / sculpted-to-DSCR (requires an iterative solver — the approach whose bogus Greene citation was removed in CRIT-1; when built, the Newton-Raphson / goal-seek solve is documented inline in code).
- **Amortization basis:** straight-line, mortgage-constant. Sculpted-to-DSCR deferred.
- **Recompute on prepayment:** configurable; default **re-amortize** over remaining term.

## Fee Modeling — LOCKED

- **Fee types (v0.x):** arrangement, commitment/unused-line, exit, prepayment penalty (declining schedule or make-whole), agency, legal-cost passthrough. **Deferred:** OID (amortizes into yield, needs YTM treatment). All v0.x fees are cash outflows on their funding/payment date. *(LOW-5.)*
- **Treatment:** cash outflows on the date, not netted against interest; shown separately.
- **Periodic fee accrual basis:** same day-count as the tranche unless a fee-specific basis is supplied.

## Reserves — LOCKED

- **Reserve types:** DSRA, IRA, MRA, capex, lease-up, TI/LC.
- **DSRA draw / replenish / release (LOCKED — resolves pass-2 "inert DSRA"):**
  - **Draw:** when period CFADS is insufficient to cover scheduled debt service, the DSRA is drawn to cover the shortfall (down to zero). This is the mechanism by which negative or sub-debt-service CFADS (MED-5 pass-through) is absorbed rather than silently ignored.
  - **Replenish:** the DSRA is topped back up to its required balance from subsequent surplus CFADS, **ahead of any equity distribution and ahead of discretionary sweep application**, and behind scheduled senior debt service.
  - **Release:** remaining balance released at final maturity (or per a documented trigger).
- **IRA (LOCKED):** funded at close → opening reserve balance at period 0; released on stabilization trigger. No construction-period drawdown (operations-only horizon). *(MED-2.)*
- **Sizing rules:** N months debt service (DSRA), N months interest (IRA), % revenue (MRA), schedule-based (capex), trigger-based (lease-up). Documented per type.
- **Funding priority:** pre-funded at close vs. from operations vs. hybrid — default per reserve type.
- **Required vs. discretionary:** required/contractual reserve funding is an explicit waterfall step **below debt service and above the sweep** (see Waterfall Priority); it is deducted once in the ECF sweep base. It is **never** netted into CFADS. Discretionary reserve top-ups, if any, rank with permitted distributions.
- **LC alternative:** `lc_funded=True` — no cash reserve, treated as "available" for shortfall.

## Waterfall Priority (Single Ordered Sequence) — LOCKED

Each operating period, available cash (CFADS) is applied in **one acyclic priority order** (resolves the pass-3 MED that the priority was never stated as a single sequence). This is the default; specific tranche seniority is configurable within these constraints, but the ordering is always a strict sequence with no cycles:

1. **Senior fees and administrative expenses** (agency, trustee, servicing) not already in opex.
2. **Senior debt service** — interest, then scheduled principal (pari-passu within the senior group, pro-rata by current balance). If CFADS is insufficient, **draw the DSRA** to cover the shortfall (Reserves).
3. **Required reserve funding / replenishment** — DSRA back to required balance, then other required reserves. Ranks below debt service, above all subordinate uses.
4. **Mezzanine / subordinate debt service** — interest, then scheduled principal.
5. **Mandatory prepayments and ECF cash sweep** — event-triggered mandatory prepayments and the leverage-banded ECF sweep (ECF as defined in Cash Sweep Mechanics).
6. **Permitted equity distributions** — blocked entirely under a covenant lock-up / cash-trap. Excluded SPV tax distributions, if supplied as inputs, are permitted here even during lock-up (Scope/MED-1).
7. **Residual cash to equity.**

The ordering is asserted acyclic and total: every dollar of CFADS is assigned to exactly one step, and no step depends on a later step. Default: senior reserve replenishment (step 3) ranks ahead of mezzanine debt service (step 4) — a senior-protective convention; configurable where a deal's ICA reverses it.

## Covenant Pack — LOCKED

- **Ratios and their inline definitions (no external authority; arithmetic is self-defining):**
  - **DSCR** = CFADS ÷ scheduled debt service, per period. Trailing / forward-looking and average-vs-minimum are configurable.
  - **LLCR** = PV(CFADS from the test date to **loan maturity**, discounted at the senior debt cost) ÷ current senior debt balance. DSRA balance may be added to the numerator (configurable; default excluded). *(Resolves pass-2 LLCR discount-rate/horizon gap.)*
  - **PLCR** = PV(CFADS from the test date to **end of project life**, discounted at the senior debt cost) ÷ current debt balance. Horizon extends beyond loan maturity to the project/asset/concession life.
  - Discount rate for LLCR/PLCR = the weighted senior debt cost, configurable and disclosed in the audit log.
  - LTV, debt yield, Debt/EBITDA, fixed-charge coverage, interest coverage — each defined inline by formula at implementation.
- **Testing frequency:** quarterly / semi-annual / annual, annual averages where applicable; configurable per covenant. **No covenant is tested before period 0** (operations-only horizon).
- **Covenant types:** maintenance / springing / incurrence.
- **Three-tier cushion:** performance (minimum), trap (trigger — cash trap / sweep), default (acceleration). Configurable.
- **Breach-output labeling (LOCKED, HIGH-2 + pass-2/pass-3 terminology):** every breach signal, cash-trap activation, and default computation is emitted as a **"mechanical test result computed by the engine from user-supplied CFADS and the deal terms."** (The engine computes debt service, so the label does not claim the result is purely user-supplied — pass-3 MED.) Output does not assert "event of default" or "acceleration available" as conclusions; it reports "test result: DSCR 0.82x below the 1.00x default threshold — acceleration is a contractual consequence the parties' documents assign to this result, not a determination by this engine." The disclaimer appears **adjacent to every breach flag**, not only in headers.

## Cash Sweep Mechanics — LOCKED

- **Sweep types:** mandatory (ECF above thresholds), discretionary (borrower election), event-triggered (covenant breach).
- **Leverage-banded step-downs:** e.g., 100% / 75% / 50% / 0% across configurable leverage bands.
- **ECF definition — LOCKED (HIGH-1 + pass-2 reserve double-count):** single formula for both CRE and PF —
  **ECF = CFADS − scheduled debt service − required reserve funding/replenishment − permitted distributions − permitted capex (growth/discretionary only).**
  CFADS is net of maintenance capex only (see Cash Flow Source Assumptions), so the ECF formula deducts **growth/discretionary capex only** (never maintenance capex — that would double-count). Required reserve funding/replenishment is deducted here **once**, matching its position in the Waterfall Priority (below debt service, above the sweep). It is *not* in CFADS, so there is no double-count. *(Resolves HIGH-1 and the pass-2/pass-3 reserve-funding treatment.)*
- **Exclusions from sweep:** permitted acquisitions, permitted distributions below leverage threshold, working-capital fluctuations. Configurable.
- **Application order:** configurable (senior pro-rata / last-out-first).

## Cure Rights — LOCKED

- **Equity cure:** deemed EBITDA boost vs. cash injection (configurable).
- **Caps:** size cap ($X or % EBITDA), frequency cap (N per 12 months / over life), max consecutive cures.
- **Overcure:** configurable (counts against next period vs. returned).
- **Mulligan:** configurable flag, default **off**.

## Mandatory Prepayments — LOCKED

- **Triggers:** ECF sweep, asset-sale proceeds, insurance/condemnation, debt incurrence, change of control, equity issuance.
- **Reinvestment rights:** configurable window (typical 12–18 months) per trigger.
- **Application order:** senior pro-rata to scheduled amort, then next maturity, then revolver. Configurable.
- **Premium:** none by default (optional prepayments may carry call protection).

## Default and Remedies — LOCKED

- **Default categories (LOCKED — pass-3 MED):** **payment default and covenant default are engine-computed mechanical test results** (the engine has the cash flows and thresholds to test them). **Bankruptcy, cross-default, and judgment are external legal events the engine cannot determine — they are user-supplied event inputs**, and the engine only propagates their consequences (e.g., automatic acceleration flag) when supplied. Output never asserts that a bankruptcy/cross-default/judgment has occurred.
- **Grace periods (default, configurable):** payment 5 business days, covenant 30 days, bankruptcy 0 days. "Business days" resolve on the U.S. Federal Reserve calendar under Modified Following.
- **Post-default interest:** default-rate spread, default **+2.00%**, configurable.
- **Acceleration / EoD:** the engine computes when contractual thresholds are crossed and **labels the result as a mechanical test result** (see Covenant Pack). It does not declare a legal event of default.
- **Intercreditor standstill:** senior exclusive-enforcement window before mezz can act; default per ICA.

## Call Protection — LOCKED

- **Non-call period:** hard NC for N years (configurable).
- **Declining call schedule:** e.g., NC-2, 102, 101, par (configurable per tranche).
- **Make-whole:** discount of remaining scheduled cash flows to a comparable-treasury reference. **Spread is a required input with no default** — T+50 / T+25 are market approximations, not published conventions, and are not hard-coded. *(LOW-1.)*
- **Yield maintenance only** in v0.x; defeasance deferred.
- **Par-call windows:** configurable (typical last 3–6 months at par).

## Cash Flow Source Assumptions — LOCKED

- **CFADS is an INPUT.** **Canonical definition (LOCKED — resolves pass-2 CRE-CFADS gap and the pass-3 CRITICAL):** CFADS = **cash available for debt service**, computed **net of opex, cash taxes, and maintenance capex only** — uniform across CRE and project finance. **Reserve funding is NOT netted into CFADS** — it is a use that ranks *below* debt service and is applied as an explicit waterfall step (see Waterfall Priority and Reserves). Netting reserves into CFADS would rank them above debt service and understate every coverage ratio (the pass-3 CRITICAL); it is prohibited.
  - **Project finance:** revenues − opex − cash tax − maintenance capex.
  - **CRE:** NOI − maintenance capex − TI/LC. (NOI is pre-capex; this nets maintenance capex once, so the ECF formula does not deduct maintenance capex again.)
- **Sign convention (MED-5):** positive CFADS = cash available for debt service.
- **Period dating (MED-5):** period-end. LLCR/PLCR/DSCR assume period-end CFADS.
- **Negative CFADS (MED-5):** passed through as-is; the DSRA-draw mechanism (see Reserves) surfaces and absorbs the shortfall. The engine does not raise on negative CFADS.
- **Capex and reserve classification is an INPUT-PREPARER responsibility (LOCKED — resolves pass-2 capex-boundary MED):** the maintenance-vs-growth capex split and the required-vs-discretionary reserve split are supplied by the input preparer. The engine **cannot verify** these classifications — its audit assertions verify arithmetic (principal trace, interest reconciliation, source/use tie-out), not the economic classification of an input. This is documented as an explicit limitation.
- **Construction draw schedules:** inputs to the upstream projection only; the engine starts at operations.
- **Stress scenarios:** engine accepts a list of CFADS streams (base / downside / severe) and runs the waterfall on each. Stress generation is not the engine's job.

## Required vs. Optional Parameters — LOCKED

- **Required (raise `InvalidInputError`):** `deal_close_date`, `operations_start_date` (period 0), `period_frequency` (M/Q/SA/A), `tranches`, `cfads_stream`.
- **Required with validation:** `data_currency` (ISO 4217), `reporting_basis` (calendar / fiscal).
- **Optional with documented defaults:** `day_count` (per tranche-type default), `business_day_convention` (Modified Following), `payment_calendar` (U.S. Federal Reserve), `sofr_calendar` (SIFMA US Government Securities), reserve sizing (per type), covenant levels (none by default — explicit only).
- All optional defaults documented inline in code AND here (single source of truth).

## Validation Tests (Built-In) — LOCKED

These audit assertions are the **primary defensibility mechanism for numeric output**:
- **Source/use tie-out at close:** sum of sources = sum of uses; `SourceUseImbalanceError` above tolerance.
- **Principal trace:** opening + draws − scheduled amort − prepayments − sweeps = closing, per tranche per period. Asserted every period.
- **Interest accrual reconciliation:** rate × average balance × day-count fraction = period interest, within tolerance.
- **Reserve roll-forward:** opening reserve + funding − draws + replenishment = closing, per reserve per period (covers the new DSRA draw/replenish logic).
- **DSCR audit table:** CFADS, debt service, DSCR per period, arithmetic auditable.
- **Capital account roll-forward (equity residual):** contributions − distributions = ending balance.
- All assertions raise typed exceptions, never silently swallow.

## Output Schema — LOCKED

- **Primary outputs:** period table (DataFrame), tranche-level summary, covenant status table, source/use statement, audit log.
- **Period table columns:** `period_index`, `period_end_date`, `cfads`, `debt_service_by_tranche`, `principal_by_tranche`, `interest_by_tranche`, `reserve_balances`, `reserve_draws`, `sweep_amount`, `equity_distribution`, `covenant_status`, `dscr`.
- **Audit log:** every per-period decision (sweep triggered, DSRA drawn/replenished, covenant test result, cure applied) with rationale, discount rate used for LLCR/PLCR, and the "mechanical test result" label on breach entries.
- **Export formats:** DataFrame, Excel (openpyxl), JSON.

## Language Guardrails (Strictly Enforced) — LOCKED

- No credit judgments ("investable," "approvable," "creditworthy," "recommended").
- No forward-looking statements not grounded in input; projection inputs yield outputs labeled as projections.
- **Standard disclaimer:** "Mechanical waterfall computation only. Not a credit recommendation. CFADS inputs are user-supplied projections, not modeled cash flows."
- **No legal conclusions in output (LOCKED — pass-2):** breach and default results are reported as mechanical test results, never as "event of default," "acceleration available," or equivalent legal conclusions stated as fact (see Covenant Pack / Default and Remedies).
- **Two-layer defensibility (HIGH-2 + MED-6):**
  1. **Language layer** — three-location disclaimer (report rendering, `DealResult.limitations`, `DealResult.interpretation` if added) with a through-function regression test; plus the mechanical-test-result label adjacent to every breach flag.
  2. **Numeric layer (primary)** — the audit-assertion pattern (Validation Tests) is the primary defensibility mechanism: principal trace, interest reconciliation, reserve roll-forward, source/use tie-out, and the audit log let a reviewer verify the numbers are internally correct. A disclaimer does not make a wrong number defensible; the audit trail does.

## Limitations (Documented in 3+ Places: methodology.md, DealResult.limitations, every report, _limitations_doc.md) — LOCKED

- No NOI / CFADS projection modeling
- No construction-period modeling; the engine's clock starts at operations/stabilization (period 0)
- **Engine does not verify capex classification (maintenance vs. growth) or reserve classification (required vs. discretionary) — these are input-preparer responsibilities**
- No tax modeling; no SPV tax-distribution (phantom-income) modeling
- No derivatives / hedge accounting
- No equity promote / carried interest (debt waterfall; equity is residual only)
- No CMBS bond-level tranching
- No A/B note structures or B-piece shortfall mechanics
- No preferred-equity / quasi-debt tranche
- No tax credit equity flips
- No defeasance (yield maintenance only)
- No OID modeling
- No sculpted-to-DSCR amortization (deferred — requires iterative solver)
- No ACT/ACT day-count (30/360, ACT/360, ACT/365F only)
- Single-currency only

## Definitional Basis (No External Authority) — LOCKED

After two audit rounds in which asserted external authorities failed verification, the methodology **does not attribute its mechanics to published standards.** Instead:
- Every computed metric (DSCR, LLCR, PLCR, ECF, LTV, debt yield) is **defined inline by its formula** — arithmetic definitions are self-defensible and require no citation.
- Market conventions (leverage-banded sweep step-downs, cure caps, default-rate spread, grace periods) are described **as common market conventions**, with configurable values and no claim to a specific published standard.
- **Removed and not to be reintroduced** (each failed external verification): Greene §17.x (Ch. 17 is discrete-choice econometrics, not numerical methods); "SIFMA CMBS Investor Reporting Package" (the IRP is CREFC, and is a reporting standard, not covenant methodology); Moody's CMBS Surveillance criteria (bond/pool-level, not loan-level); "LSTA MCAP June 2025 edition" (no such final edition; the MCAPs are syndicated-corporate boilerplate that deliberately exclude ECF/cure/covenant terms); "S&P Project Finance Framework" (misnamed/retired; S&P criteria are DSCR-centric and do not define LLCR/PLCR; an issue-rating source, not loan-level); MBA "underwriting standards" (MBA publishes origination volume statistics, not underwriting standards, and the engine performs no underwriting).
- **General reference (non-load-bearing, not relied on for correctness):** E. R. Yescombe, *Principles of Project Finance* — standard practitioner treatment of LLCR/PLCR. Listed as further reading only; the engine's LLCR/PLCR correctness rests on the inline formulas above, not on this text.

## Release Process — LOCKED

- CI-driven publish (working principle #8): `release.yml` verify-version → build → test-wheel → publish.
- OIDC Trusted Publisher configured BEFORE first CI publish. No local-tree publishes.
- Version-guard via tomllib, Python 3.11+ in publish step. All actions SHA-pinned.
- Dual-import shim: `waterfall_py` and `waterfallpy` resolve to the same package (WP #6).
- CHANGELOG from day 1 (WP #7).
- Methodology bundled in wheel via importlib.resources (fair-lending-screener v0.2.0 pattern).

## Audit Discipline (For Reference)

Defensible-output category (a counterparty's lawyer might read output in litigation). Apply the fair-lending-screener pattern:
- Self-audit before publish (WP #3)
- Hostile second-pass audit in a fresh session (WP #4) — **this resolved methodology must pass a 0-CRIT/0-HIGH re-audit before code is written**
- Through-function regression tests for every guardrail
- No "this test exists" assumption — verify the test runs and asserts on the right thing

---

**Next steps:**
1. Fresh-session hostile re-audit #2 of THIS resolved methodology (must confirm 0 CRIT / 0 HIGH; confirm no external authority claim remains and the inline definitions are internally consistent).
2. On re-audit GO, scope the v0.x feature set into a build plan against the locked decisions.
3. THEN write code against the locked methodology (negative-case-first tests, principal-trace / reserve-roll-forward / audit-assertion discipline).

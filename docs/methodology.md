# waterfall-py: Methodology

> **STATUS: METHODOLOGY GATE CLEARED.** Pass-7 fresh-session hostile re-audit returned **GO (0 CRIT / 0 HIGH)** against the pass-6 resolution; the residual pass-7 MED-1 (proceeds-path equity gate under a trap) and two LOWs (facility-repayment prose; lineage numbering) are folded into this revision. Cleared for the v0.x build-plan stage. Lineage below retained for audit provenance. Lineage: skeleton (53294fc) → first hostile audit `methodology_audit.md` (2 CRIT / 5 HIGH / 6 MED / 5 LOW) → mechanical fixes f87f689 (CRIT-1/2, HIGH-3/5) → first resolution 9875f44 → **second hostile audit `methodology_audit_pass2.md` (methodology-review-pass2, ffb2af9): NO-GO, 2 CRIT / 4 HIGH / 6 MED / 4 LOW** → pass-2 resolution → **third hostile audit `methodology_audit_pass3.md` (methodology-review-pass3, a28168c): NO-GO, 1 CRIT / 0 HIGH / 5 MED / 6 LOW** → this revision. Pass-2 removed the authority-per-mechanic approach and defines every computed metric inline by formula. The pass-3 CRITICAL was self-inflicted: the pass-2 fix for the ECF double-count netted required reserve funding *into* the CFADS definition, which ranks reserves above debt service (backwards) and manufactures false covenant breaches. This revision **removes that term from CFADS** (CFADS is again cash available for debt service, net of maintenance capex only), moves required reserve funding to an explicit waterfall step below debt service, and states a single ordered waterfall. **Fourth hostile audit `methodology_audit_pass4.md` (methodology-review-pass4, 3b41060): NO-GO, 0 CRIT / 1 HIGH / 2 MED / 6 LOW** — the pass-3 CRITICAL was confirmed correctly fixed, but the new Waterfall Priority ladder and the carried-over ECF formula contradicted each other on three of four terms (self-inflicted, same class as prior rounds). This revision makes **ECF a quantity *derived from* the ladder** (ECF ≡ cash remaining after ladder steps 1–4) so the two can no longer drift, separates non-CFADS mandatory-prepayment proceeds from the operating waterfall, repoints the Reserves cross-references at the ladder by rung number, adds a cash-conservation assertion, and closes all six carried LOWs. **Fifth hostile audit `methodology_audit_pass5.md` (methodology-review-pass5, 5b04166): NO-GO, 0 CRIT / 1 HIGH / 1 MED / 2 LOW** — pass-4's ECF↔ladder fix converged, but the cash-conservation assertion it added asserted "steps 1–7 sum to CFADS," which is false whenever the DSRA draws or a reserve releases (those are additional cash sources). This revision corrects the assertion to **sources (CFADS + reserve draws + reserve releases + applied event proceeds) = uses**, gives released-reserve cash an explicit destination (the separate proceeds path), sub-orders the step-6 junior bucket with caps, and makes the DSCR denominator scope explicit. **Sixth hostile audit `methodology_audit_pass6.md` (methodology-review-pass6, 14c519c): NO-GO, 0 CRIT / 1 HIGH / 2 MED / 2 LOW** — the pass-5 cash-conservation fix was correct but *closed*: it enumerated a fixed four-source set and omitted other modeled inflows (equity cure injections, revolver/delayed-draw draws), so the assertion fired spuriously in cure/draw periods (same class, one mechanism out). This revision makes the cash-conservation identity **general** (all modeled sources = all modeled uses, enumerated from the per-period ledger, not a hardcoded list — structurally drift-proof), defines cash-trap as a forced 100% sweep so no trapped cash leaks to equity (MED-1), adds the step-1 fee and non-CFADS-source columns to the output schema (MED-2), and closes both LOWs. Per working principle #1, this resolved methodology must pass a fresh-session hostile re-audit (0 CRIT / 0 HIGH) BEFORE any analysis code is written.

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
- **SPV tax distribution provisions** (phantom-income distributions to equity). Out of v0.x scope: the engine does not model the phantom-income calculation and **does not fund tax distributions from the waterfall**. If a user needs them, they are supplied as ordinary distribution inputs and handled outside the engine's covenant/lock-up logic. *(Scope agrees with the Cash-trap/lock-up paragraph — no lock-up carve-out exists; resolves the pass-2 tax-distribution interaction cleanly.)*
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
- **Facility draws as a cash source:** revolver / delayed-draw fundings taken in an operating period are a **non-CFADS cash source** in the period cash-conservation identity (Validation Tests) — the drawn cash enters the ledger and funds the use it finances; it increases the tranche balance in the principal trace. Not folded into CFADS.

## Fee Modeling — LOCKED

- **Fee types (v0.x):** arrangement, commitment/unused-line, exit, prepayment penalty (declining schedule or make-whole), agency, legal-cost passthrough. **Deferred:** OID (amortizes into yield, needs YTM treatment). All v0.x fees are cash outflows on their funding/payment date. *(LOW-5.)*
- **Treatment:** cash outflows on the date, not netted against interest; shown separately.
- **Periodic fee accrual basis:** same day-count as the tranche unless a fee-specific basis is supplied.

## Reserves — LOCKED

- **Reserve types:** DSRA, IRA, MRA, capex, lease-up, TI/LC.
- **DSRA draw / replenish / release (LOCKED — resolves pass-2 "inert DSRA"):**
  - **Draw:** when period CFADS is insufficient to cover **senior scheduled debt service (step 2)**, the DSRA is drawn to cover the shortfall (down to zero). This is the mechanism by which negative or sub-debt-service CFADS (MED-5 pass-through) is absorbed rather than silently ignored. The draw is a cash source in that period (see Validation Tests cash-conservation).
  - **Replenish:** the DSRA is topped back up to its required balance at **Waterfall Priority step 3** — below step 2 (senior debt service), above step 4 (mezzanine service) and step 5 (the mandatory ECF sweep). (References the ladder by rung, so it cannot be read against it — resolves MED-2.)
  - **Release:** remaining balance released at final maturity (or per a trigger — see Triggers below). **Released cash is a source in the release period and is applied on the separate proceeds path — to outstanding debt in priority order, then to equity residual** (it is NOT swept as ECF; releases are not operating excess). This gives released reserve cash an explicit destination (resolves pass-5 LOW).
- **IRA (LOCKED — pass-through only; resolves LOW-5):** the interest reserve account exists to fund construction-period interest, which is out of scope. In the operations-only horizon it is therefore **a pass-through opening balance**: carried in at period 0 as available liquidity and released on its user-supplied trigger period. The engine does **not** draw it for construction interest (there is no construction period modeled). If a deal has no operating-period interest-reserve mechanic, IRA is simply omitted.
- **Sizing rules:** N months **senior** debt service (DSRA — sized on the same base it is drawn against and the default DSCR tests), N months interest (IRA), % revenue (MRA), schedule-based (capex), trigger-based (lease-up). Documented per type. *(Resolves pass-6 LOW-2.)*
- **Triggers (LOCKED — resolves LOW-6):** every reserve trigger (DSRA/IRA release, lease-up funding/release, stabilization) must resolve to **a user-supplied period index or an engine-computable test** (e.g., sustained DSCR ≥ x for n periods). Triggers may **never** reference an un-modeled condition such as physical occupancy — the engine tracks no occupancy/lease-up state and the period table carries no such field.
- **Funding priority:** pre-funded at close vs. from operations vs. hybrid — default per reserve type.
- **Required vs. discretionary:** required/contractual reserve funding is **Waterfall Priority step 3** — below step 2 (senior debt service), above step 4 (mezzanine) and step 5 (the mandatory ECF sweep); it is deducted once in the ECF base (step 5), which is derived from the ladder. It is **never** netted into CFADS. Discretionary reserve top-ups rank at **step 6** with permitted junior uses.
- **LC alternative:** `lc_funded=True` — no cash reserve, treated as "available" for shortfall.

## Waterfall Priority (Single Ordered Sequence) — LOCKED

Each operating period, **operating cash (CFADS)** — supplemented at the steps they fund by any non-CFADS sources (DSRA draws and cure injections at step 2; user-scheduled facility draws where applicable) — is applied in **one acyclic priority order**. Reserve releases and event proceeds are applied on the separate proceeds path (below), not through these steps. This is the default; specific tranche seniority is configurable within these constraints, but the ordering is always a strict sequence with no cycles. **This ladder is the single source of truth for cash priority; the ECF sweep base (Cash Sweep Mechanics) is *derived from* it, not defined independently.**

1. **Senior fees and administrative expenses** (agency, trustee, servicing) not already in opex.
2. **Senior debt service** — interest, then scheduled principal (pari-passu within the senior group, pro-rata by current balance). If CFADS is insufficient to cover senior debt service, the shortfall is covered by **non-CFADS sources, in order: the DSRA draw (Reserves), then an equity cash-injection cure if elected (Cure Rights)**. (Facility revolver/delayed-draw draws are user-scheduled financing inputs, not an autonomous shortfall-cover mechanic in v0.x.) Each such source is enumerated in the cash-conservation identity.
3. **Required reserve funding / replenishment** — DSRA back to required balance, then other required reserves.
4. **Mezzanine / subordinate debt service** — interest, then scheduled principal.
5. **Mandatory ECF cash sweep** — the leverage-banded sweep applies `sweep% × ECF` to **debt prepayment in priority order: senior first, then mezzanine only once senior is fully retired** (never pari-passu across seniority), where **ECF ≡ the cash remaining after steps 1–4** (see Cash Sweep Mechanics). If the sweep retires all debt, any remaining swept cash joins step-7 residual. Event-driven mandatory prepayments funded by **non-CFADS proceeds** (asset sale, insurance/condemnation, debt/equity issuance) are **not** part of this operating-cash ladder — they apply their own proceeds on a separate application (see Mandatory Prepayments).
6. **Permitted junior uses from retained ECF** — the un-swept `(1 − sweep%) × ECF`, applied in this **internal sub-order**: **6a** permitted growth/discretionary capex (up to its permitted-capex basket cap); **6b** discretionary reserve top-ups; **6c** permitted equity distributions (most junior; subject to a no-default condition and a leverage-based basket cap). Each cap is configurable; cash beyond a binding cap flows to the next sub-step, then to step 7.
7. **Residual cash to equity** — reached when **no** cash-trap/lock-up is active, **or** when a trap is active but all debt has already been fully retired (the trap is then moot — see below). Otherwise no residual reaches equity while a trap is active and debt remains outstanding.

**Cash-trap / lock-up behavior (LOCKED — resolves pass-6 MED-1 and pass-7-code CRITICAL C1):** a trap-tier covenant breach forces the step-5 ECF sweep to **100%**. Retained ECF is then 0, so **steps 6 and 6c distributions receive no cash** — no junior use or distribution occurs while the trap is active. **The trapped sweep cash prepays debt in priority order: senior first, then mezzanine.** **Edge — trap retires all debt (resolves C1):** if the forced 100% sweep **fully retires all outstanding debt** in a period, the trap is moot (no lender remains to protect) and any **residual operating cash then flows to step 7 equity** — mirroring the separate proceeds path. Without this, residual cash would be neither swept (no debt left) nor distributed (steps 6–7 gated), stranding cash and firing the cash-conservation assertion. So: residual-to-equity is blocked while the trap is active **and debt remains outstanding**; once debt is fully retired the block lifts. (The separate proceeds path's equity leg is gated on the identical rule — see below — so neither route reaches equity while debt is outstanding under a trap, and both release residual to equity once debt is fully retired.) (SPV tax distributions are out of v0.x scope — see Scope — and are not funded from the waterfall; the earlier "permitted at 6c during lock-up" carve-out is removed. Scope and this paragraph now state the same rule.)

**Separate proceeds path (not part of the operating-cash ladder):** reserve releases and event-driven proceeds (asset sale, insurance/condemnation, debt/equity issuance) are applied to outstanding debt in priority order, then to equity — they are not swept as ECF (consistent with the CFADS-only scope of steps 1–7). **Under an active cash-trap/lock-up this path's equity leg is gated in parallel with step 7:** proceeds are applied to outstanding debt only, and any residual is **held (not paid to equity) while debt remains outstanding**. Once all debt is fully retired the trap is moot — no lender remains to protect — so a proceeds/release residual arising *after* full debt retirement is not trapped and flows to equity. *(Resolves pass-7 MED-1: the equity leg is now gated, matching line-86's guarantee.)*

The ordering is asserted **acyclic**: no step depends on a later step. **Totality is enforced across all modeled cash, not just CFADS**, by the general period cash-conservation assertion (Validation Tests): the sum of all modeled sources = the sum of all modeled uses. Default: senior reserve replenishment (step 3) ranks ahead of mezzanine debt service (step 4) — a senior-protective convention; configurable where a deal's ICA reverses it. Because ECF is defined as the residual after step 4, growth capex, discretionary reserve top-ups, and permitted distributions sit at step 6 (junior to the sweep) and are **not** deducted in the ECF base — the pass-4 HIGH-1 contradiction cannot recur.

## Covenant Pack — LOCKED

- **Ratios and their inline definitions (no external authority; arithmetic is self-defining):**
  - **DSCR** = CFADS ÷ scheduled debt service, per period. **Denominator scope is explicit (resolves pass-5 LOW):** default = **senior scheduled debt service** (senior DSCR); a **total DSCR** variant (senior + mezzanine service — mirroring the ECF base, whose "debt service" is senior + mezz) is configurable; each covenant declares which it tests. Trailing / forward-looking and average-vs-minimum are configurable.
  - **LLCR** = PV(CFADS from the test date to **loan maturity**, discounted at the senior debt cost) ÷ current senior debt balance. DSRA balance may be added to the numerator (configurable; default excluded). *(Resolves pass-2 LLCR discount-rate/horizon gap.)*
  - **PLCR** = PV(CFADS from the test date to **end of project life**, discounted at the senior debt cost) ÷ **current senior debt balance** (same denominator as LLCR — resolves LOW-3). Horizon extends beyond loan maturity to the project/asset/concession life. **PLCR, and the LLCR project-life horizon, are project-finance-only** — CRE deals have no project/concession life and do not compute PLCR; CRE coverage uses DSCR, LTV, and debt yield. *(Resolves LOW-2.)*
  - Discount rate for LLCR/PLCR = the weighted senior debt cost, configurable and disclosed in the audit log.
  - **Applicability:** DSCR, LTV, debt yield apply to both CRE and PF; LLCR/PLCR and Debt/EBITDA/fixed-charge coverage are used where the deal type warrants (PF and corporate-style credits respectively). Each metric's applicability is recorded with its result.
  - **Division-by-zero / undefined (LOCKED — resolves LOW-1):** once the relevant denominator is zero — scheduled debt service = 0 (DSCR) or current debt balance = 0 (LLCR/PLCR/LTV), e.g., after full repayment via sweeps/prepayments — the covenant is **not tested** and the ratio is reported as **n/a** (never ∞, 0, or a raised error). Testing resumes only if a positive balance/debt service returns.
  - LTV, debt yield, Debt/EBITDA, fixed-charge coverage, interest coverage — each defined inline by formula at implementation.
- **Testing frequency:** quarterly / semi-annual / annual, annual averages where applicable; configurable per covenant. **No covenant is tested before period 0** (operations-only horizon).
- **Covenant types:** maintenance / springing / incurrence.
- **Three-tier cushion:** performance (minimum), trap (trigger — cash trap / sweep), default (acceleration). Configurable.
- **Breach-output labeling (LOCKED, HIGH-2 + pass-2/pass-3 terminology):** every breach signal, cash-trap activation, and default computation is emitted as a **"mechanical test result computed by the engine from user-supplied CFADS and the deal terms."** (The engine computes debt service, so the label does not claim the result is purely user-supplied — pass-3 MED.) Output does not assert "event of default" or "acceleration available" as conclusions; it reports "test result: DSCR 0.82x below the 1.00x default threshold — acceleration is a contractual consequence the parties' documents assign to this result, not a determination by this engine." The disclaimer appears **adjacent to every breach flag**, not only in headers.

## Cash Sweep Mechanics — LOCKED

- **Sweep types:** mandatory (ECF above thresholds), discretionary (borrower election), event-triggered (covenant breach).
- **Leverage-banded step-downs:** e.g., 100% / 75% / 50% / 0% across configurable leverage bands.
- **ECF definition — LOCKED (derived from the ladder; resolves pass-4 HIGH-1):** ECF is **not an independent formula** — it is the cash remaining after Waterfall Priority steps 1–4, so it can never contradict the ladder. Equivalently:
  **ECF = CFADS − senior fees & admin (step 1) − senior debt service (step 2) − required reserve funding/replenishment (step 3) − mezzanine debt service (step 4).**
  Every deduction is a ladder rung *above* the sweep, and every rung above the sweep is a deduction — the set matches exactly. "Debt service" here is **all** debt service ranking above the sweep: senior (step 2) **and** mezzanine (step 4). CFADS is net of maintenance capex only, so maintenance capex is not deducted again. **Growth/discretionary capex, discretionary reserve top-ups, and permitted distributions are NOT deducted** — they are step-6 junior uses (6a/6b/6c) funded from retained ECF, below the sweep. Required reserve funding is deducted here exactly once, mirroring its single cash outflow at step 3 (it is not in CFADS). Same formula for CRE and PF. *(Resolves HIGH-1: distributions and growth capex removed from the base, senior fees added, mezz made explicit.)*
- **Sweep and retained ECF:** the sweep captures `sweep% × ECF` (per leverage band); the retained `(1 − sweep%) × ECF` funds step-6 permitted junior uses subject to lock-up/conditions.
- **Carve-outs from the sweep base:** because ECF is the residual after steps 1–4, sweep carve-outs are handled as adjustments to CFADS *before* the ladder (e.g., non-recurring/non-operating proceeds and working-capital true-ups excluded from operating CFADS), not as deductions inside the ECF formula. Permitted acquisitions and permitted distributions are junior uses (step 6), **not** sweep-base carve-outs — keeping the base consistent with the ladder. Configurable.
- **Application order:** configurable (senior pro-rata, or sequential by seniority/maturity). "Sequential" here means ordinary seniority/maturity ordering of prepayment among the in-scope tranches — **not** a last-out/FLLO or agreement-among-lenders construct (those, with A/B and B-piece mechanics, are out of scope; see Limitations). *(Resolves LOW-4.)*

## Cure Rights — LOCKED

- **Equity cure:** deemed EBITDA boost vs. cash injection (configurable). A **cash-injection cure is a non-CFADS cash source** in the period cash-conservation identity (Validation Tests) — it enters the ledger as equity cash and funds the use it cures (typically senior debt service at step 2); it does **not** contaminate CFADS, which stays operating-only.
- **Caps:** size cap ($X or % EBITDA), frequency cap (N per 12 months / over life), max consecutive cures.
- **Overcure:** configurable (counts against next period vs. returned).
- **Mulligan:** configurable flag, default **off**.

## Mandatory Prepayments — LOCKED

- **Two distinct cash sources (LOCKED — resolves MED-1):** the **ECF sweep** is funded by operating CFADS and lives at step 5 of the Waterfall Priority. **Event-driven mandatory prepayments** — asset-sale proceeds, insurance/condemnation, debt incurrence, change of control, equity issuance — are funded by **non-operating proceeds**, not CFADS. They are applied on their **own separate application** (below) and are **not** part of the operating-cash ladder; the "every dollar of CFADS is assigned to exactly one step" invariant covers operating CFADS only.
- **Reinvestment rights:** configurable window (typical 12–18 months) per proceeds trigger.
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
- **Make-whole:** discount of remaining scheduled cash flows to a comparable-treasury reference. **Spread is a required input with no default** — T+50 / T+25 are market approximations, not published conventions, and are not hard-coded. *(pass-1 LOW-1, make-whole spread.)*
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

- **Required (raise `InvalidInputError`):** `deal_close_date`, `operations_start_date` (period 0), `period_frequency` (M/Q/SA/A), `tranches`, `cfads_stream`. Validated constraint: `operations_start_date >= deal_close_date` (close is the source/use snapshot; accrual and periods begin at operations start).
- **Required with validation:** `data_currency` (ISO 4217), `reporting_basis` (calendar / fiscal).
- **Optional with documented defaults:** `day_count` (per tranche-type default), `business_day_convention` (Modified Following), `payment_calendar` (U.S. Federal Reserve), `sofr_calendar` (SIFMA US Government Securities), reserve sizing (per type), covenant levels (none by default — explicit only).
- All optional defaults documented inline in code AND here (single source of truth).

## Validation Tests (Built-In) — LOCKED

These audit assertions are the **primary defensibility mechanism for numeric output**:
- **Source/use tie-out at close:** sum of sources = sum of uses; `SourceUseImbalanceError` above tolerance.
- **Period cash-conservation (sources = uses) — LOCKED (general ledger identity, not a fixed enumeration; resolves pass-6 HIGH):** each period, the sum of **all** cash sources the engine models = the sum of **all** cash uses, within tolerance, or `WaterfallImbalanceError`. **The engine builds both sides from the actual per-period ledger, not from a hardcoded list** — so introducing or exercising any modeled cash mechanism cannot silently falsify the identity (the recurring failure mode of prior passes, where a fixed source list omitted a mechanism modeled elsewhere). Both sides are enumerated from the ledger at assertion time; the following are **illustrative of what the engine currently models, not a closed set**:
  - **Sources (any cash entering the period ledger):** operating CFADS; DSRA/reserve draws; reserve releases; **equity contributions and cash-injection cures** (Cure Rights); **facility draws** — revolver/delayed-draw fundings (Principal Amortization / Capital Stack); applied event proceeds (asset-sale/insurance/etc.). Every non-CFADS source is exactly that — **not** folded into CFADS, which stays operating-only per its definition.
  - **Uses (any cash leaving the ledger):** Waterfall Priority steps 1–7 (fees, senior DS, reserve funding, mezz DS, ECF sweep, junior uses incl. discretionary reserve top-ups, residual); facility repayments; and the separate applications of reserve releases and event proceeds (to outstanding debt, then equity). ("Facility repayments" means financing outflows on a facility tranche, **counted once** — a repayment effected via the step-5 sweep or step-2 scheduled amort *is* that step, not a second use; the ledger tags each cash movement to a single entry.)
  Because the identity is over **all** modeled cash, it holds — and does not fire spuriously — in surplus, DSRA-draw, reserve-release, **mid-life equity-cure**, and **revolver-draw** periods alike. This enforces "every dollar accounted, exactly once" and is drift-proof against future mechanism additions.
- **Principal trace:** opening + facility draws (delayed-draw/revolver fundings) − scheduled amort − prepayments − sweeps = closing, per tranche per period. ("Facility draws" here are tranche fundings — distinct from DSRA *reserve* draws.) Asserted every period.
- **Interest accrual reconciliation:** rate × average balance × day-count fraction = period interest, within tolerance.
- **Reserve roll-forward:** closing balance = opening + required funding/replenishment (step 3) + discretionary top-ups (step 6b) − draws − releases, per reserve per period. (Draws and releases are cash *sources* to the waterfall; required funding is the step-3 cash *use* and discretionary top-ups are the step-6b cash *use* — both raise the reserve balance. Ties out with the period cash-conservation assertion, which counts both as uses.)
- **DSCR audit table:** CFADS, debt service, DSCR per period, arithmetic auditable.
- **Capital account roll-forward (equity residual):** opening + contributions − distributions = ending balance.
- All assertions raise typed exceptions, never silently swallow.

## Output Schema — LOCKED

- **Primary outputs:** period table (DataFrame), tranche-level summary, covenant status table, source/use statement, audit log.
- **Period table columns:** `period_index`, `period_end_date`, `cfads`, `fees` (step-1 senior fees & admin), `facility_draws`, `equity_contributions` (cures/contributions), `debt_service_by_tranche`, `principal_by_tranche`, `interest_by_tranche`, `reserve_balances`, `reserve_draws`, `reserve_releases`, `proceeds_applied` (event proceeds / release prepayments), `sweep_amount`, `junior_uses` (step-6 6a/6b/6c breakdown), `equity_distribution`, `covenant_status`, `dscr`. (Columns surface every source and every use in the period cash-conservation identity — step-1 fees through step-7 residual, plus all non-CFADS sources — so a reviewer can tie the identity out from the table alone.)
- **Audit log:** every per-period decision (**fees paid**, **facility draw taken**, sweep triggered, DSRA drawn/replenished/released, **equity cure/contribution applied**, event proceeds applied, covenant test result) with rationale, discount rate used for LLCR/PLCR, and the "mechanical test result" label on breach entries.
- **Export formats:** DataFrame, Excel (openpyxl), JSON.

## Language Guardrails (Strictly Enforced) — LOCKED

- No credit judgments ("investable," "approvable," "creditworthy," "recommended").
- No forward-looking statements not grounded in input; projection inputs yield outputs labeled as projections.
- **Standard disclaimer:** "Mechanical waterfall computation only. Not a credit recommendation. CFADS inputs are user-supplied projections, not modeled cash flows."
- **No legal conclusions in output (LOCKED — pass-2):** breach and default results are reported as mechanical test results, never as "event of default," "acceleration available," or equivalent legal conclusions stated as fact (see Covenant Pack / Default and Remedies).
- **Two-layer defensibility (HIGH-2 + MED-6):**
  1. **Language layer** — three-location disclaimer (report rendering, `DealResult.limitations`, `DealResult.interpretation` if added) with a through-function regression test; plus the mechanical-test-result label adjacent to every breach flag.
  2. **Numeric layer (primary)** — the audit-assertion pattern (Validation Tests) is the primary defensibility mechanism: principal trace, interest reconciliation, reserve roll-forward, period cash-conservation (sources = uses), source/use tie-out, and the audit log let a reviewer verify the numbers are internally correct. A disclaimer does not make a wrong number defensible; the audit trail does.

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
1. ✅ Fresh-session hostile re-audit — **pass 7 returned GO (0 CRIT / 0 HIGH)**; methodology gate closed.
2. Scope the v0.x feature set into a build plan against the locked decisions (see `waterfall-py_v0x_build_plan.md`).
3. Build on a feature branch → fresh hostile audit of the CODE (fresh session) → fix → Jay ships (tag/push/publish). Negative-case-first tests; principal-trace / reserve-roll-forward / cash-conservation / capital-account assertions enforced.

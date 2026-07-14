# waterfall-py: Methodology Skeleton — Second-Pass Audit Findings

> **STATUS: ACTIVE.** Hostile second-pass audit of the methodology skeleton drafted in commit 53294fc. No code has been written against this skeleton. All CRITICAL and HIGH findings must be resolved before writing analysis code (working principle #1). DECISIONS TO LOCK markers in the skeleton are NOT findings — they are the author's own open items.

Audit conducted by hostile reviewer in fresh Claude Code session.
Result: **2 CRITICAL, 5 HIGH, 6 MEDIUM, 5 LOW, 10 CLEAN items verified.**

---

## CRITICAL

### CRIT-1: Greene §17.x citation is doubly wrong
- **Section:** `## Citations (To Verify)`
- **The claim:** "Greene §17.x (numerical methods) — if iterative solver needed for sculpted amort"
- **Why it's wrong:** Verified via web search. Chapter 17 of Greene's *Econometric Analysis* (all major editions) covers discrete choice models (logit, probit, multinomial). Numerical methods are in Appendix E and Chapter 15. The section number is wrong. More fundamentally, Greene is an econometrics textbook — it has no content on project finance sculpted amortization iterative solvers. An expert reviewer picking up this methodology document will lose trust in all other citations the moment they check this one. This is not "if you squint it fits" — it is a flatly wrong citation.
- **Direction:** Replace with the actual reference for Newton-Raphson / goal-seek approaches in financial modelling (e.g., Bodmer *Project Finance in Theory and Practice*, or a numerical methods text). If no specific source is needed, drop the citation and document the iterative solve approach inline in code comments.

---

### CRIT-2: "SIFMA CMBS Investor Reporting Package" does not exist as named
- **Section:** `## Citations (To Verify)`
- **The claim:** "SIFMA CMBS Investor Reporting Package — covenant testing conventions (note: loan-level only, not bond-level)"
- **Why it's wrong:** Verified via web search. The CMBS Investor Reporting Package is published by **CREFC** (CRE Finance Council), not SIFMA. SIFMA does not publish a CMBS IRP. The document being cited almost certainly does not exist under the name given. The parenthetical "(note: loan-level only, not bond-level)" makes the error worse by claiming a bond-level reporting standard is being used for loan-level analysis — that's not how the CREFC IRP works either (it covers both levels). No version of this citation survives external review.
- **Direction:** Replace with the correct document: CRE Finance Council (CREFC) Investor Reporting Package, with the applicable version number. Note that CREFC IRP is primarily a reporting standard, not a covenant testing methodology — verify whether it actually supports the specific claim being cited.

---

## HIGH

### HIGH-1: ECF formula mixes LSTA base (EBITDA) with project-finance base (CFADS) — produces wrong numbers for PF deals
- **Section:** `## Cash Sweep Mechanics`
- **The claim:** "ECF (excess cash flow) definition: standard LSTA-style — CFADS minus debt service minus permitted distributions minus permitted capex minus reserve funding."
- **Why it's wrong:** The LSTA ECF definition starts from Adjusted EBITDA, then deducts cash taxes, interest, scheduled principal, capex, and changes in working capital. The methodology instead starts from CFADS and then deducts "permitted capex." For project finance deals where CFADS is explicitly defined as revenues minus opex minus tax minus **maintenance capex** (see `## Cash Flow Source Assumptions`), deducting "permitted capex" from CFADS again double-counts maintenance capex in the sweep calculation. For CRE deals where CFADS approximates NOI (pre-capex), the formula may be correct. The same formula cannot serve both cases without a capex-treatment clarification. Code written against this definition will produce understated ECF sweeps for project finance deals.
- **Direction:** Either (a) define separate ECF formulas for CRE vs. project finance contexts with explicit capex treatment documented for each, or (b) define "permitted capex" in the ECF formula as growth/discretionary capex only and document that maintenance capex must not be double-counted by the CFADS input preparer.

---

### HIGH-2: "No credit judgment" guardrail is unenforceable against covenant breach outputs
- **Section:** `## Language Guardrails (Strictly Enforced)` and `## Covenant Pack`
- **The claim:** "Output never produces credit judgments. No 'investable,' 'approvable,' 'creditworthy,' 'recommended.'"
- **Why it's weak:** The covenant section produces DSCR covenant breach signals, cash trap activations, and event-of-default computations. These are credit determinations by operational effect regardless of label. An OCC examiner reviewing a bank's credit file that contains engine output showing "DSCR = 0.82x — covenant default, acceleration available" will treat that as a credit determination. The guardrail as written blocks specific adjectives but does not address the interpretive risk of numeric breach outputs. A counterparty's counsel will make the same argument in deal dispute litigation. The disclaimer language alone does not contain the risk.
- **Direction:** Redraw the guardrail to address covenant breach output specifically: label all breach signals as "mechanical test results based on user-supplied inputs" and require the disclaimer to appear adjacent to every breach flag in the output, not only in summary headers.

---

### HIGH-3: "Project finance often 30/360" is convention drift — ACT/360 dominates US PF bank loans
- **Section:** `## Interest Mechanics`
- **The claim:** "Default per tranche-type convention (CRE senior usually ACT/360, project finance often 30/360 — confirm)"
- **Why it's wrong:** ACT/360 is the dominant day-count for US commercial bank loans, which includes US project finance bank debt. 30/360 is primarily a residential mortgage and fixed-income bond convention. In European project finance, ACT/365 (Fixed) is more common, not 30/360. Naming 30/360 as the project finance default, even with a "— confirm" flag, will anchor the subsequent decision in the wrong direction. Any senior project finance practitioner will catch this immediately.
- **Direction:** Reverse the default: project finance bank loans default to ACT/360 (same as CRE). If bond-form documentation is supported (which it isn't in v0.x scope), 30/360 may apply there. The "— confirm" flag is appropriate; the stated default before confirming is not.

---

### HIGH-4: Business-day convention and holiday calendar are completely unspecified
- **Section:** Throughout (Interest Mechanics, Principal Amortization, Covenant Pack, Output Schema)
- **The claim:** The methodology assumes the engine produces `period_end_date` values and computes stub periods, grace periods in "business days," and interest accrual over actual day counts.
- **Why it's a gap:** No business-day adjustment rule is specified (Following, Modified Following, Preceding, End-of-Month). No holiday calendar is named. For date arithmetic in a financial computation engine, these are foundational decisions that affect every computed date. A period end date falling on a Saturday or U.S. bank holiday produces different results under different conventions. Grace periods stated as "5 business days" require a calendar. This gap is not a DECISIONS TO LOCK marker — it is simply missing from the document.
- **Direction:** Add a dedicated subsection (or decision item) specifying: default business-day convention (suggest Modified Following), default holiday calendar (suggest U.S. Federal Reserve), and whether multi-currency deals would require separate calendars (deferred to when multi-currency is added).

---

### HIGH-5: Moody's CMBS Surveillance cited for loan-level covenant testing
- **Section:** `## Citations (To Verify)`
- **The claim:** "Moody's CMBS Surveillance criteria — covenant testing"
- **Why it's wrong:** Moody's CMBS Surveillance methodology covers pool-level and bond-level credit monitoring — default probability and loss-given-default on CMBS securities. It is not a source for loan-level covenant testing conventions. This is the same misattribution as the SIFMA/CREFC error (CRIT-2): using a bond/pool-level source to support a loan-level claim. The specific document being cited needs to be identified; "Moody's CMBS Surveillance criteria" as a general reference for covenant testing is not verifiable.
- **Direction:** Identify the actual Moody's or S&P source for loan-level covenant testing conventions, or drop the citation and rely on LSTA MCAP as the primary loan-level covenant reference. Do not cite bond-level surveillance methodology for loan-level behavior.

---

## MEDIUM

### MED-1: SPV tax distribution provisions are a scope gap
- **Section:** `## Scope` (Out of scope)
- **The claim:** "Tax credit equity waterfalls (LIHTC, NMTC, HTC, ITC partnership flips)... not this tool."
- **The gap:** The out-of-scope exclusion covers tax credit equity structures. It does not address **tax distribution provisions in non-tax-credit SPVs** — a standard provision in project finance SPVs that distributes cash to equity to cover taxes on phantom income (pass-through income in excess of distributions). These distributions are part of the waterfall and interact with DSRA sizing and cash trap mechanics. They are not "tax credit equity" — they are SPV operating provisions. The methodology neither includes nor explicitly excludes them.
- **Direction:** Add a single explicit exclusion: "Tax distribution provisions in SPV entities (phantom income distributions to equity holders) are out of scope; treat as user-specified distribution inputs if needed."

---

### MED-2: Construction IRA scope contradiction
- **Section:** `## Scope` (Out of scope) vs. `## Reserves` and `## Cash Flow Source Assumptions`
- **The contradiction:** The Scope section says "construction draw schedules... inputs only" and lists them as out of scope. Cash Flow Source Assumptions says "No construction-period modeling beyond accepting a draw schedule and computing interest reserve drawdown." The Reserves section lists IRA (interest reserve) as in scope with its own funding and release rules. These statements cannot all be true simultaneously: computing IRA drawdown during a construction period **is** construction-period modeling. The IRA draw depends on outstanding construction loan balance per period, which depends on the draw schedule.
- **Direction:** Reconcile: either define "construction-period modeling" to explicitly include IRA drawdown computation (and make that the stated in-scope perimeter), or declare that IRA is only modeled post-stabilization (funded at close, released on trigger).

---

### MED-3: A/B note split mechanics absent despite B-piece listed as a tranche type
- **Section:** `## Capital Stack Architecture`
- **The gap:** The Capital Stack section lists "B-piece" as a supported tranche type. A/B note structures (senior A note typically held in conduit or syndicated; junior B note sold to B-piece buyer) have specific waterfall mechanics that differ from ordinary senior/mezz priority: interest shortfall absorption (B takes shortfall before A), appraisal reduction amounts (ARA) that reduce the master servicer's advance obligation, and loss allocation in sequential vs. pro-rata pay structures. None of these are addressed. If a user models an A/B deal, the engine's standard seniority queue will produce incorrect results.
- **Direction:** Either scope out A/B note structures explicitly ("B-piece is treated as a subordinate tranche; A/B-specific shortfall mechanics are out of scope in v0.x") or add a section defining the specific waterfall behavior for A/B splits.

---

### MED-4: World Bank PPP Reference Guide cited for DSCR conventions — VERIFY-NEEDED
- **Section:** `## Citations (To Verify)`
- **The claim:** "World Bank PPP Reference Guide — project finance debt sizing and DSCR conventions"
- **Why it needs verification:** The World Bank PPP Reference Guide (3rd Edition, 2017) covers PPP procurement frameworks, risk allocation, and contractual structures. It discusses DSCR in context but is primarily a procurement/policy document, not a lender-practice source for DSCR sizing conventions. Project finance DSCR conventions are more authoritatively sourced from S&P or Moody's project finance criteria, or from IFC/EBRD lending guidelines. The citation may be substantiable but needs a specific section or page reference, not just the document name.
- **Direction:** VERIFY-NEEDED: Pull the World Bank PPP Reference Guide 3rd Ed. and confirm there is a substantive DSCR convention section. If the relevant content is there, add a section/chapter reference. If not, replace with a more appropriate source (S&P project finance criteria, IFC investment guidelines).

---

### MED-5: CFADS sign convention and period dating are implicit and unstated
- **Section:** `## Cash Flow Source Assumptions` and `## Output Schema`
- **The gap:** The methodology specifies that CFADS is an input, but does not state: (a) sign convention — is positive CFADS a cash inflow (expected) or outflow? What does the engine do with negative CFADS in a stress scenario? (b) period dating — are cash flows dated at period start or period end? The output schema shows `period_end_date` but does not specify whether CFADS is assumed to arrive at the end of the period or is distributed over the period. In mortgage math, payments are end-of-period; in project finance DCF, CFADS is typically modeled as mid-period or end-of-period. This choice propagates through every LLCR/PLCR computation.
- **Direction:** Add explicit statements: CFADS sign convention (positive = cash available for debt service), period dating convention (period-end or mid-period), and negative CFADS handling (pass through as-is, allowing DSR calculation to show shortfall, or raise an error).

---

### MED-6: Three-location language guardrail transfers weakly from fair-lending-screener
- **Section:** `## Language Guardrails` and `## Limitations`
- **The issue:** The methodology directly maps the fair-lending-screener three-location enforcement pattern (methodology.md, DealResult.limitations, every report, _limitations_doc.md) to waterfall-py. For fair-lending-screener, the three-location pattern protects against a statistical claim ("adjusted disparity") being misunderstood as a discrimination finding — a specific interpretive harm tied to specific output language. For a debt waterfall engine, the analogous defensibility gap is **numeric audit trail integrity**: can a user verify that the principal trace is correct, that the sweep was computed correctly, that the covenant test used the right inputs? Placing a disclaimer in three locations does not address this; audit assertions and the period-by-period audit log do. The pattern transfers for the specific "no credit judgment" language risk, but it is misapplied as the primary defensibility mechanism for the broader category of output misuse.
- **Direction:** Keep the three-location disclaimer pattern for the language guardrail (it transfers). Add a parallel section specifying the audit assertion pattern as the primary defensibility mechanism for numeric output: principal trace, interest accrual reconciliation, and the audit log are the counterparts to the disclaimer, not supplements to it.

---

## LOW

### LOW-1: Make-whole spread levels (T+50, T+25) stated without citation — convention drift risk
- **Section:** `## Call Protection`
- **The claim:** "Make-whole computation: T+50, T+25, fixed spread to comparable treasury."
- **Why it's weak:** T+50 and T+25 are market approximations, not published conventions. Spread levels in yield maintenance / make-whole provisions vary significantly by credit quality, deal vintage, market conditions, and lender type. Stating specific spreads as "the" make-whole computation without a source creates a convention-drift risk if these are coded as defaults.
- **Direction:** Either drop the specific spread levels and document them as configurable (no default), or add a citation to a specific market survey or LSTA guidance if one exists.

---

### LOW-2: ULI/NAIOP cited for CRE underwriting standards — not primary authorities
- **Section:** `## Citations (To Verify)`
- **The claim:** "ULI / NAIOP — CRE underwriting standards"
- **Why it's weak:** ULI (Urban Land Institute) publishes real estate research and best practices; NAIOP publishes development industry guidance. Neither is the primary authority for commercial mortgage underwriting conventions. The Mortgage Bankers Association (MBA), Fannie Mae/Freddie Mac multifamily guidelines, or OCC CRE lending guidance would be more defensible sources for underwriting standards. The claim needs a specific document title and section.
- **Direction:** VERIFY-NEEDED: Identify what specific claim ULI/NAIOP is being cited to support. If it's property-type-specific data (e.g., CRE cap rates), ULI may be appropriate; if it's underwriting conventions, replace with MBA or bank regulatory guidance.

---

### LOW-3: LSTA MCAP citation lacks edition, year, and version
- **Section:** `## Citations (To Verify)`
- **The claim:** "LSTA (Loan Syndications and Trading Association) — Model Credit Agreement Provisions, ECF definitions, cure rights"
- **Why it's weak:** LSTA publishes updated MCAP drafts periodically (most recently June 2025 per web search). "LSTA Model Credit Agreement Provisions" without a version date is not pinpointed enough for a methodology document that claims to follow "LSTA-style" ECF definitions. Different editions have materially different ECF formulations.
- **Direction:** Add the specific MCAP edition or date (e.g., "LSTA MCAP, [month] [year] edition, §[X]"). The June 2025 draft is the most recent as of this audit.

---

### LOW-4: Leap-year handling and ACT/ACT variants are silent
- **Section:** `## Interest Mechanics`
- **The claim:** The methodology lists ACT/ACT as a supported day-count convention.
- **The gap:** ACT/ACT has multiple variants with different leap-year treatment: ISDA (each period separately calculated), ICMA (ISDA bond basis, 1/365 or 1/366 per day), AFB (French convention). The methodology does not specify which ACT/ACT variant is used. For loan computations spanning February 29, the three variants produce different results.
- **Direction:** Specify which ACT/ACT variant is supported. ACT/ACT ISDA is the most common in derivatives; ACT/ACT ICMA is more common in bond math. For loan computations, ACT/ACT is rare — consider whether it is actually needed or whether ACT/365(Fixed) covers the use cases.

---

### LOW-5: OID absent from fee types section
- **Section:** `## Fee Modeling`
- **The gap:** Original Issue Discount (OID) — upfront economic cost of a loan structured as a discount to par rather than a cash fee — is absent from the fee types list. OID has different accounting and economic treatment from arrangement fees (amortized over the loan life into interest income/expense, affects yield-to-maturity calculation). In leveraged loans and some project finance transactions, OID is common (e.g., a $100M loan funded at 99 cents on the dollar). Without OID modeling, the engine will understate borrower cost and overstate lender return for discounted facilities.
- **Direction:** Add OID as a fee type in v0.x scope or explicitly exclude it ("OID treatment deferred to v0.x; all fees treated as cash outflows on funding date").

---

## CLEAN (verified as defensible)

1. **Tax credit equity exclusion** — LIHTC/NMTC/HTC/ITC exclusion is clearly drawn and correctly distinguishes equity flip structures from debt waterfalls.
2. **PIK toggle default** — Capitalize to principal at end of period is correct market convention; configurable per tranche is appropriate.
3. **Three-tier covenant structure** — Performance / trap / default (minimum / trigger / acceleration) is the correct description of standard covenant architecture.
4. **Leverage-banded ECF sweep step-downs** — 100%/75%/50%/0% banding with configurable thresholds correctly describes standard LSTA leveraged loan mechanics.
5. **SOFR and Term SOFR indices** — Correct post-LIBOR transition references; 1M/3M/6M Term SOFR variants are accurate.
6. **Cure rights structure** — Size cap, frequency cap (N per 12 months), consecutive cure caps, and deemed EBITDA boost vs. cash injection election are correct descriptions of market convention.
7. **Typed exception hierarchy** — Pattern transfers cleanly. Appropriate to raise `InvalidInputError`, `SourceUseImbalanceError`-style exceptions; never silently swallow.
8. **Principal trace validation** — Opening balance + draws – scheduled amort – prepayments – sweeps = closing balance, asserted every period, is the correct computational discipline.
9. **Source/use tie-out at close** — Correct: sum of sources = sum of uses at deal close, with typed exception on mismatch above tolerance.
10. **CI/release process** — OIDC Trusted Publisher, SHA-pinned actions, tomllib version guard, dual-import shim — all transfer correctly from fair-lending-screener.

---

## Hostile-Reviewer Simulations

### Former OCC CRE Examiner (30 min)

Reviewing a bank's use of this tool's methodology before examining the bank's model governance.

- **~5 min:** Flags the "no credit judgment" guardrail against covenant breach output. "Exhibit A says DSCR = 0.82x, covenant default triggered, acceleration available. That's in the bank's credit file. Calling it a 'mechanical computation' doesn't change what it is — it's a credit determination the bank relied on. Your disclaimer needs to appear at every breach signal, not just in the report header."
- **~15 min:** Notes the complete absence of business-day convention and holiday calendar. "What business-day rule does this use? If the engine computes period-end dates without a named calendar and convention, it won't match the credit agreement dates. That's a model governance failure under OCC Bulletin 2011-12."
- **~25 min:** Checks SIFMA citation. "There's no SIFMA CMBS Investor Reporting Package. That's CREFC. If the citations are wrong, I'm going to check every other claim in this document."

### Counterparty Litigation Counsel (30 min)

Reviewing methodology document produced in discovery in a waterfall dispute.

- **~10 min:** Targets ECF formula. "Counsel, your expert's tool defines ECF starting from CFADS. My client's credit agreement defines ECF starting from Adjusted EBITDA. Those are different starting points. The tool's ECF calculation is not the contractual ECF calculation. Any sweep amount your expert computed is methodologically inconsistent with the document it purports to analyze."
- **~20 min:** Notes absence of A/B note mechanics. "The methodology lists 'B-piece' as a supported tranche type. It doesn't describe how A/B interest shortfalls are allocated. My client has an A/B structure. Your expert used this tool on a deal the methodology explicitly doesn't cover."
- **~28 min:** Flags construction IRA contradiction. "The methodology says construction draw schedules are 'inputs only' and out of scope. It also says the engine 'computes interest reserve drawdown.' Which is it? If the construction period IRA computation is wrong, the entire post-construction waterfall is seeded with the wrong opening balance."

### Senior Project Finance MD (30 min)

Reviewing a junior analyst's model before it goes to credit committee.

- **Immediately:** "30/360 for project finance? No. Every US project finance bank loan I have done uses ACT/360. The bond market uses 30/360; banks don't. This default is wrong — fix it before anyone else reads this."
- **~8 min:** "Where's the business-day convention? What happens when a period end date is a federal holiday? 'Modified Following' needs to be in here, and you need a named holiday calendar. Credit committee will ask."
- **~15 min:** "Greene Section 17 for sculpted amortization? I've used that book. Chapter 17 is logit and probit. It has nothing to do with sculpted amort. Whoever put this citation in here either didn't check it or confused it with the appendix. Either way, it has to come out."
- **~22 min:** "CFADS minus permitted capex in the ECF sweep formula — for project finance, CFADS already nets maintenance capex. What does 'permitted capex' mean in a project finance context where there basically is no growth capex? You're either double-counting or you're deducting zero. Neither is right without explicit documentation."

---

*Audit basis: methodology skeleton commit 53294fc. No code reviewed — this audit is methodology-only per working principle #1.*

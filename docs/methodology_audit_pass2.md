# waterfall-py: Methodology — Second-Pass (Re-Audit) Findings

> **STATUS: ACTIVE.** Hostile re-audit of the *resolved* methodology (`docs/methodology.md`, `methodology-review` branch, commit 9875f44) in a fresh session. The first-pass audit (`methodology_audit.md`, `methodology-audit` branch) found 2 CRIT / 5 HIGH / 6 MED / 5 LOW against the skeleton (53294fc). The resolution claims to have addressed every open finding. This re-audit verifies each claimed resolution is *real* (not reworded), runs the external citation checks the resolution deferred to "re-audit," and hunts for new defects introduced by the scope-outs and locked defaults. No code exists.

Audit conducted by hostile reviewer in fresh Claude Code session. External facts verified via web search (LSTA, S&P Global Ratings, MBA).

**Result: 2 CRITICAL, 4 HIGH, 6 MEDIUM, 4 LOW.**

## VERDICT: **NO-GO.**

GO requires 0 CRITICAL and 0 HIGH. This re-audit finds 2 CRITICAL and 4 HIGH. **Do not write code against this methodology.**

The headline: the resolution's own re-audit gate reads *"verify the two VERIFY-NEEDED citations are pinned or dropped."* They are neither. **Every surviving/added citation in the "RESOLVED" Citations section fails external verification** — the section that opens *"Citation discipline (learned from CRIT-2 / HIGH-5): never cite a bond/pool-level source for loan-level behavior, and pin every citation to an edition/section"* reintroduces the *identical* failure mode three times. The first pass's mechanical citation fixes (Greene/SIFMA/Moody's) hold; the *replacement* citations are as broken as the originals.

---

## CRITICAL

### CRIT-1: LSTA MCAP is the wrong document for ECF/cure, the wrong market for CRE/PF, and the June 2025 "edition" does not exist
- **Section:** `## Citations — RESOLVED / VERIFY-AT-RE-AUDIT` (line 177); load-bearing for `## Cash Sweep Mechanics` (HIGH-1 ECF) and `## Cure Rights`.
- **The claim:** *"LSTA — Model Credit Agreement Provisions (MCAP), June 2025 edition — ECF definitions, cure rights. (Pins LOW-3; the June 2025 edition was the most recent as of the audit…)"*
- **Why it's wrong (three independent failures, verified via lsta.org):**
  1. **The edition does not exist.** There is no *final* "June 2025 edition" of the MCAPs. What is dated June 2025 is a **draft** ("Draft – Model Credit Agreement Provisions (MCAPs), Jun 4 2025"), an exposure draft of Article 17 (Confidentiality). The most recent *finalized* MCAPs are **May 1, 2023 (reposted July 8, 2024)** (prior final: May 4, 2022). So the pin that "resolves LOW-3" points at a nonexistent final edition — **LOW-3 is not resolved**, it is mis-pinned to a draft.
  2. **The document does not contain ECF or cure definitions.** The LSTA MCAPs are, by design, the *administrative/boilerplate machinery* provisions only — tax gross-up/yield protection, agency, assignment ("Successors and Assigns"), defaulting-lender, disqualified-institution, ERISA reps. Economic/business terms — **Excess Cash Flow sweeps, equity cure rights, and financial covenants — are deliberately excluded** from the MCAPs and negotiated deal-by-deal. Citing the MCAPs as the authority for ECF and cure mechanics is a category error: those terms are not in the document. (The LSTA reference that *does* cover economic terms is the treatise *The LSTA's Complete Credit Agreement Guide*, not the MCAPs form.)
  3. **The market is wrong.** The MCAPs are, in the LSTA's own words, "suitable primarily for leveraged finance transactions" — broadly-syndicated **corporate** leveraged loans. They are not written for **CRE** (property-level, DSCR/mortgage-driven) or **project finance** (SPV, contracted-cashflow, reserve-account waterfalls) — the two markets this tool targets.
- **Why it's CRITICAL:** This is the CRIT-2 failure mode reintroduced — a source cited for content and a market it does not cover. It is the sole cited authority for the HIGH-1 ECF formula and the entire Cure Rights section. A senior practitioner who opens the MCAPs to check the ECF definition and finds it isn't there loses trust in the whole document (the exact rationale the first pass used to rate CRIT-1/CRIT-2 critical).
- **Direction:** Drop the MCAPs pin for ECF/cure. If a leveraged-loan lineage is intended, cite *The LSTA's Complete Credit Agreement Guide* (with edition) and state explicitly that ECF/cure conventions are adapted from broadly-syndicated corporate loans and **may not match CRE or PF market practice**. For CRE/PF, cite market-appropriate sources or document the convention as an internal design decision with no external authority (permissible if labeled as such).

---

### CRIT-2: "S&P Global Ratings — Project Finance Framework" is misnamed, retired, does not cover LLCR/PLCR, and is an issue-rating source used for loan-level conventions
- **Section:** `## Citations — RESOLVED / VERIFY-AT-RE-AUDIT` (line 178); load-bearing for `## Covenant Pack` (DSCR/LLCR/PLCR).
- **The claim:** *"S&P Global Ratings — Project Finance Framework — LLCR/PLCR and DSCR sizing conventions (loan-level, project-finance). Primary source for DSCR conventions, replacing the World Bank PPP Reference Guide… (Resolves MED-4…)"*
- **Why it's wrong (verified via S&P criteria index + S&P/Maalot criteria PDFs):**
  1. **Wrong / retired name.** No current S&P document is titled "Project Finance Framework." The real predecessor was *"Project Finance Framework **Methodology**"* (2014, republished through 2018–19) — the cited name drops "Methodology." That entire generation was **superseded on December 14, 2022** by *"General Project Finance Rating Methodology"* (core) and *"Sector-Specific Project Finance Rating Methodology."* The citation names a document that no longer exists in the form implied.
  2. **It does not cover LLCR/PLCR.** S&P's project-finance criteria are **DSCR-centric** — minimum DSCR (default-risk proxy), average DSCR, and a downside-DSCR resilience test feeding an Operations Phase Business Assessment. **LLCR and PLCR do not appear** in the S&P framework; they are bank-lender/financial-modeling metrics. Attributing "LLCR/PLCR conventions" to S&P attributes metrics the source does not use.
  3. **It is the antipattern the doc swore off.** S&P is a **ratings agency**; its PF criteria exist to assign **issue/issuer credit ratings to project debt**. Labeling it a *"loan-level, project-finance"* lender-practice source is precisely *"citing a bond/[issue]-level source for loan-level behavior"* — the discipline the Citations section claims to have learned from CRIT-2/HIGH-5. The shared word "DSCR" masks the mismatch (S&P uses min/downside DSCR to *rate* debt; it does not document how lenders *size/covenant* it).
- **Why it's CRITICAL:** This is the *sole* cited authority for the DSCR/LLCR/PLCR conventions that anchor the in-scope Covenant Pack, and it fails on name, coverage, and level-of-analysis simultaneously. **MED-4 is not resolved** — World Bank PPP was swapped for a citation that is defective on more axes than the one it replaced.
- **Direction:** If a ratings source is genuinely intended, rename to *"S&P Global Ratings, General Project Finance Rating Methodology, Dec 14, 2022"* **and** reclassify it as a bond/issue-rating source (not loan-level). Do **not** attribute LLCR/PLCR to S&P — those are standard financial-modeling formulas; document them as internal conventions or cite a lender/modeling source. Confirm which DSCR object (min vs. average vs. downside) the engine's DSCR covenant represents.

---

## HIGH

### HIGH-1: DSRA is never drawn to cover a shortfall — the debt-service reserve is inert for its core purpose, and this contradicts the negative-CFADS pass-through
- **Section:** `## Reserves` (lines 57–62) vs. `## Cash Flow Source Assumptions` (line 118, MED-5).
- **The defect:** The DSRA is listed (line 57), sized as "N months of debt service" (line 59), and its only stated behavior is **"Release rules: DSRA at maturity"** (line 61). There is **no rule for drawing the DSRA when CFADS < debt service** — the exact event a debt-service reserve exists to absorb. Meanwhile MED-5 (line 118) says negative/short CFADS is "passed through as-is so the… shortfall surfaces," with no mention of the DSRA covering it first. The only "available for shortfall purposes" language in the whole doc is attached to the **LC alternative** (line 62), implying — by omission — that the cash DSRA is *not* drawn on shortfall. A DSRA that is only "released at maturity" and never drawn is economically inert.
- **Why it's HIGH:** For any deal with a DSRA (i.e., essentially every project-finance and structured CRE deal in scope), the engine will report shortfalls/defaults in periods a real DSRA would have cured, and it will over-report cash trapped at maturity. The covenant/default cascade is seeded off wrong period balances. This is a missing core waterfall mechanic, not a citation nit.
- **Direction:** Specify DSRA (and IRA post-stabilization) **draw-on-shortfall and replenishment** rules: when CFADS < debt service, draw the reserve to the sizing floor before recording a payment shortfall; replenish from the waterfall (and where in priority); only *then* pass through any residual shortfall. State the interaction with cash-trap/lock-up explicitly.

### HIGH-2: The construction-period scope-out collides with "accrue from close," draw schedules, and reserves-funded-at-close — in-scope operating output silently depends on a deferred construction model
- **Section:** `## Scope` (line 21) + `## Interest Mechanics` (line 40, "accrue daily") + `## Reserves` (line 58, IRA "funded at close") + `## Cash Flow Source Assumptions` (line 119) + `## Required Parameters` (line 124, `deal_close_date`).
- **The defect:** The engine requires `deal_close_date`, accepts construction **draw schedules as inputs**, funds DSRA/IRA **at close**, and **accrues interest daily from close** — but **construction-period modeling (including IRA drawdown that services construction interest) is out of scope**, and CFADS is an **operating input**. The doc never defines whether period 0 is the **close date** (construction start) or the **operations start**. If the modeled timeline begins at close: interest accrues on drawn construction debt, CFADS during construction is typically zero/negative, and the mechanism that normally services construction interest (IRA drawdown) is explicitly *not* modeled → by line 118 the engine "passes through the shortfall," manufacturing **spurious defaults in every construction period**, or forcing the user to fabricate CFADS to cover construction interest. Either way the post-construction waterfall is seeded from a wrong opening state — the same "wrong opening balance" concern the first-pass litigation sim raised, now created by the *resolution* rather than fixed by it.
- **Why it's HIGH:** This is the "tight core secretly requires a deferred capability" failure the scope-out was supposed to prevent. The IRA-funded-at-close + accrue-from-close + construction-out triad cannot all hold for a real construction deal without a defined construction-phase handling.
- **Direction:** State unambiguously that period 0 = **operations start** and that the engine models **post-construction/post-stabilization only**, with tranches entered at their **fully-drawn opening balances** and IRA as an opening reserve released on trigger — OR bring minimal construction-period interest capitalization back in scope. Then reconcile `deal_close_date`, draw schedules, and "accrue from close" with whichever perimeter is chosen (draw schedules and delayed-draw/accordion draws that occur *during* the modeled operating window are fine; construction draws are not).

### HIGH-3: The single ECF formula is only defensible for project finance — CRE CFADS composition is undefined, and the "− reserve funding" term double-counts maintenance for CRE
- **Section:** `## Cash Sweep Mechanics` (lines 77–79, HIGH-1) + `## Cash Flow Source Assumptions` (line 115) + `## Reserves` (line 57).
- **The defect:** The HIGH-1 resolution rests on "CFADS is already net of **maintenance capex**." But line 115 defines that composition **only for project finance** ("For project finance, CFADS = revenues − opex − tax − maintenance capex"). CRE is left undefined, and standard CRE convention is the *opposite*: **NOI is pre-capex**; maintenance/replacement capex and TI/LC are handled through **reserves** (the doc itself lists MRA, capex reserve, TI/LC reserve, line 57). Two consequences:
  1. **Under-deduction for CRE:** if a CRE preparer supplies CFADS = NOI (pre-capex) — the natural CRE reading — the single ECF formula (which deducts *growth* capex only) never removes maintenance capex/TI/LC → **ECF overstated → oversweep**. The doc gives the CRE preparer no instruction, so this is the likely path.
  2. **Double-count via reserves for the PF reading:** the ECF formula also subtracts **"− reserve funding."** For a deal that funds an MRA/capex reserve *and* has maintenance capex netted into CFADS, maintenance economics are deducted twice (once inside CFADS, once as reserve funding). To be correct, CRE needs CFADS **pre-maintenance-capex** (maintenance captured via reserve funding) while PF needs CFADS **net of maintenance capex** — **contradictory CFADS definitions the single formula cannot satisfy at once.**
- **Why it's HIGH:** HIGH-1 was rated because the same formula "cannot serve both cases without a capex-treatment clarification." The resolution clarified the **PF** case and declared victory for both; the **CRE half of the tool's scope is still ambiguous, and the reserves interaction reintroduces a double-count.**
- **Direction:** Define CFADS composition for **CRE** explicitly (state whether CRE CFADS is NOI pre-capex or NCF net of replacement reserves) and reconcile it with the "− reserve funding" term so maintenance is deducted exactly once per market. Add an audit assertion that ties CFADS composition to the reserve-funding and capex-deduction lines (see MED-1).

### HIGH-4: MBA is not an authority for underwriting conventions, is unpinnable, and is cited for an activity the engine does not perform
- **Section:** `## Citations — RESOLVED / VERIFY-AT-RE-AUDIT` (line 179).
- **The claim:** *"MBA — Commercial/Multifamily origination conventions — CRE underwriting-standards reference, replacing ULI/NAIOP… (Resolves LOW-2.)"*
- **Why it's wrong (verified via mba.org):** The MBA's commercial/multifamily output is **origination-volume statistics and market surveys** (Quarterly Originations Index, Annual Origination Volume Summation, Annual Rankings, Quarterly DataBook) — it **measures how much was lent, not the terms on which lending is permitted**. There is **no pinnable MBA document that defines underwriting conventions** (DSCR minimums, LTV limits, amortization standards). The authoritative, edition-pinnable sources are the **Fannie Mae / Freddie Mac multifamily guides**, **HUD/FHA MAP Guide**, and **Interagency CRE guidance (2006/2015)**. So LOW-2 swapped one non-authority (ULI/NAIOP) for another non-authority (MBA). Worse: the citation carries no title/edition, **violating the doc's own "pin every citation to an edition/section" rule** — and it *cannot* be made compliant, because no such MBA underwriting-standards document exists to pin.
- **Why it's HIGH (not LOW):** It is the third void citation in the section that explicitly claims citation discipline was learned, and it is cited for **underwriting** — an activity the engine explicitly does **not** perform (NOI/CFADS are inputs; credit judgment is out of scope, line 24). A citation with no in-scope claim to support, pointing at a non-authority, in a "RESOLVED" section, is a systemic-integrity failure, not a stylistic nit.
- **Direction:** Either delete the MBA citation (nothing in the mechanical engine needs it), or, if property-type/volume context is genuinely used, cite a specific MBA **survey edition** for **volume** claims only. For any underwriting-convention claim, cite Fannie/Freddie multifamily guide sections, the HUD MAP Guide, or the Interagency CRE guidance — with pins.

---

## MEDIUM

### MED-1: The maintenance/growth-capex boundary is operator-dependent and un-auditable — HIGH-1's anti-double-count control has no assertion behind it
- **Section:** `## Cash Sweep Mechanics` (line 79) vs. `## Validation Tests` (lines 129–138) and MED-6 (line 154).
- **The issue:** HIGH-1's fix makes correctness depend entirely on the **input preparer** classifying capex into "maintenance" (netted in CFADS) vs. "growth/discretionary" (deducted in ECF). The boundary is genuinely ambiguous in practice (life-extending overhauls, roof replacement, capacity-expanding renovation), the doc offers **no definition or guidance**, and — critically — MED-6 elevated audit assertions as *"the primary defensibility mechanism for numeric output,"* yet **there is no assertion checking capex classification or the no-double-count invariant.** The one number the first pass identified as the double-count risk is the one number with no trace. "Operable by the preparer" reduces to "the preparer is on their own."
- **Direction:** Add a capex-classification definition with examples, and a validation assertion that maintenance capex appears in exactly one place (CFADS netting) and growth capex in exactly one place (ECF deduction), surfaced in the audit log.

### MED-2: LLCR/PLCR are in-scope covenants with no discount-rate convention and no defined horizon — and PLCR is meaningless for CRE
- **Section:** `## Covenant Pack` (line 66) + `## Cash Flow Source Assumptions` (line 117).
- **The issue:** LLCR = PV(CFADS over remaining loan life)/net debt and PLCR = PV(CFADS over project life)/net debt both require a **discount rate** — never specified (typically the cost of debt / loan rate). Line 117 fixes only *dating* ("period-end CFADS"); you cannot compute an LLCR without the discount rate. PLCR additionally needs a **project-life CFADS tail beyond loan maturity**, but the period table is loan/deal-indexed with no defined post-maturity horizon. And **PLCR has no meaning for CRE** (no "project life"), yet the covenant pack lists it unscoped.
- **Direction:** Specify the LLCR/PLCR discount-rate convention, define the project-life horizon source for PLCR, and scope PLCR (and LLCR's project-life variant) to project finance only.

### MED-3: The breach label misattributes the basis of the result — DSCR breaches depend on engine-computed debt service, not just user inputs
- **Section:** `## Covenant Pack` (line 71) + `## Language Guardrails` (line 153).
- **The issue:** Every breach flag is labeled *"mechanical test result based on **user-supplied inputs**."* But a DSCR-breach signal is CFADS (user-supplied) ÷ **debt service (engine-computed** from rate/day-count/amort). Attributing the result solely to user inputs **under-claims the engine's own contribution**: if the engine miscomputes debt service, the resulting false breach is mislabeled as user-driven. In litigation that label is itself an exposure ("your label says user inputs, but the 0.82x came from *your* debt-service math"). HIGH-2 fixed *where* the label appears; it did not make the label *accurate*.
- **Direction:** Reword to "mechanical test result computed by the engine from user-supplied inputs (CFADS, covenant levels) and engine-computed values (debt service, balances)." Tie the debt-service figure in each breach entry to the interest-accrual reconciliation assertion.

### MED-4: Legal-conclusion terminology survives the "mechanical test result" label — "event of default," "acceleration," "automatic on bankruptcy"
- **Section:** `## Covenant Pack` (lines 70–71) + `## Default and Remedies` (line 102) + `## Language Guardrails` (HIGH-2).
- **The issue:** HIGH-2's label mitigates, but the *output vocabulary* still states legal determinations the tool cannot make: outputs are named **"event of default"** and **"acceleration."** Worse, line 102 says acceleration is **"automatic on bankruptcy"** — but bankruptcy is an external legal event the engine cannot determine; the engine can only act on a user-supplied bankruptcy *flag*. Labeling a signal "mechanical test result" does not stop a reviewer from reading "your tool declared an event of default and accelerated the loan." This is the residual of HIGH-2 that neither pass fully closed.
- **Direction:** Rename output states to test-threshold language ("EoD threshold breached per user-supplied covenant levels," "acceleration *available* per user-supplied terms"), and make clear bankruptcy/acceleration are driven by user-supplied event flags, not determined by the engine.

### MED-5: HIGH-4 fixed the headline business-day default but left maturity-date, EOM, adjusted-accrual, and SOFR-calendar seams
- **Section:** `## Interest Mechanics` (lines 36, 39–40).
- **The issue:** Four date-math gaps the single "Modified Following + Fed calendar" default does not cover:
  1. **Maturity date:** Modified Following is a questionable *blanket* default for the **final maturity/principal date** — practitioners generally do not extend (or, under "Modified," pull *backward* across month-end) the legal maturity; maturity dates are commonly unadjusted or carved out. Applying Modified Following uniformly can move the final payment off the legal maturity date.
  2. **End-of-Month roll:** unspecified. A deal closing on a month-end (e.g., Feb 28) has no stated rule for whether subsequent period-ends roll to month-end or to the day-of-month.
  3. **Adjusted vs. unadjusted accrual:** the doc adjusts payment dates but never states whether the ACT/360 **accrual** period follows the adjusted or unadjusted dates — a real difference in total interest over the life.
  4. **SOFR calendar:** SOFR fixings follow the **SIFMA U.S. Government Securities Business Day calendar**, not the **Federal Reserve** calendar; a single Fed-calendar default can misalign floating-rate reset/lookback dates (line 36).
- **Direction:** Carve out the maturity date (unadjusted or Following, no month-end pull-back); specify the EOM rule; state adjusted-vs-unadjusted accrual; and use the SIFMA securities calendar for SOFR fixings while keeping the Fed calendar for payment/grace-period business days.

### MED-6: SPV tax distributions (MED-1 original) collide with the covenant lock-up mechanic
- **Section:** `## Scope` (line 18) + `## Covenant Pack` (line 70).
- **The issue:** MED-1 (original) resolves SPV tax distributions by treating them as **user-specified distribution inputs** — i.e., they flow as equity distributions. But a covenant **lock-up** is defined as **"no equity distributions"** (line 70) with **no carve-out**. Mandatory SPV tax distributions normally **survive lock-up** (they cover phantom-income tax and are non-discretionary). As written, a breach would incorrectly block the tax distribution. The scope-out created a new interaction the doc does not address.
- **Direction:** State whether user-specified tax distributions are subject to or exempt from lock-up/cash-trap; the market-standard treatment (survives lock-up, capped) should be the documented default or an explicit configurable flag.

---

## LOW

### LOW-1: "last-out-first" sweep ordering implies last-out-tranche support adjacent to the scoped-out A/B mechanics
- **Section:** `## Cash Sweep Mechanics` (line 81). "Sweep application order: configurable (senior pro-rata / **last-out-first**)." Last-out priority is a unitranche/FLLO "agreement-among-lenders" construct in the same family as the A/B mechanics scoped out in MED-3. Clarify that "last-out-first" refers only to ordinary seniority ordering, not to last-out/A-B intercreditor tranching.

### LOW-2: Stabilization / lease-up triggers reference conditions absent from the engine's inputs
- **Section:** `## Reserves` (lines 58, 61) + `## Output Schema` (line 143). IRA release is on a "stabilization trigger" and lease-up reserve is "trigger-based," but the period table has no occupancy/lease-up field, and the trigger's definition (user-supplied period index vs. DSCR-computed vs. occupancy-computed) is unspecified. If any trigger is occupancy-based, the engine lacks the input. State that triggers must reduce to engine-computable quantities (e.g., a sustained-DSCR test) or a user-supplied period.

### LOW-3: Corporate/PF-only covenant metrics listed without market scoping
- **Section:** `## Covenant Pack` (line 66). Debt/EBITDA, fixed-charge coverage (corporate), PLCR (PF) and LTV/debt-yield (CRE) are pooled without noting which apply where. Harmless if all configurable, but a reviewer expects the pack to flag that PLCR/Debt-EBITDA are not CRE covenants and LTV/debt-yield are not typical PF covenants.

### LOW-4: Dead-citation names remain in the shipping methodology
- **Section:** `## Principal Amortization` (line 45) + `## Citations` (line 180). The "REMOVED… do not reintroduce" note and the inline "bogus Greene citation" reference keep Greene/SIFMA/Moody's names in the *shipped* doc. Harmless internally, but an external reviewer greps the document, hits the names, and re-raises resolved findings. Consider moving the removal log to a commit message or an internal changelog, not the methodology body.

---

## Verification of first-pass resolutions (what genuinely held)

**Confirmed resolved (CLEAN):**
- **CRIT-1 / CRIT-2 / HIGH-5 removals** — Greene §17.x, SIFMA CMBS IRP, Moody's CMBS Surveillance are **gone from all live citations** (they survive only in the line-180 "do-not-reintroduce" note; see LOW-4). Diff of f87f689 confirms the deletion. *Genuinely resolved.*
- **HIGH-3 (day-count)** — 30/360 is **no longer named as any PF default**; ACT/360 is the stated default for both CRE senior and US PF bank debt (line 38); 30/360 correctly relabeled residential/bond. *Genuinely resolved.*
- **LOW-4 (ACT/ACT)** — dropped, consistent across Interest Mechanics (line 37) and Limitations (line 170). *Resolved.*
- **LOW-5 (OID)** — scoped out consistently (lines 51, 168). *Resolved.*
- **LOW-1 (make-whole spreads)** — configurable, no default; T+50/T+25 correctly demoted to non-conventions (line 109). *Resolved.*
- **MED-5 (CFADS sign/dating/negative)** — stated as written (lines 116–118). *Resolved as drafted* (but see HIGH-1 pass-2: the negative-CFADS path exposes the missing DSRA-draw mechanic).
- First-pass CLEAN items (pari-passu pro-rata seniority, leverage-banded sweep, cure-rights *structure*, typed-exception hierarchy, principal trace, source/use tie-out, CI/release) remain CLEAN.

**Claimed resolved but NOT genuinely resolved:**
- **MED-4** — World Bank PPP dropped, but the S&P replacement is defective (CRIT-2 pass-2).
- **LOW-2** — ULI/NAIOP dropped, but the MBA replacement is defective (HIGH-4 pass-2).
- **LOW-3** — MCAP "pinned," but to a nonexistent June 2025 edition (CRIT-1 pass-2).
- **HIGH-1** — resolved for PF only; CRE half still ambiguous + reserves double-count (HIGH-3 pass-2).
- **HIGH-2** — label placed correctly, but terminology and label-accuracy residuals remain (MED-3, MED-4 pass-2).
- **HIGH-4** — headline default set, but maturity/EOM/accrual/SOFR-calendar seams remain (MED-5 pass-2).
- **MED-2** — construction contradiction removed in *statement*, but reappears as a seam vs. accrue-from-close/reserves-at-close (HIGH-2 pass-2).
- **MED-1** — SPV tax distributions excluded, but collide with lock-up (MED-6 pass-2).

---

## Hostile-Reviewer Simulations

### Former OCC CRE Examiner (30 min)
- **~4 min:** Opens the Citations section. "You told me you learned not to cite bond-level sources for loan-level behavior — then you cite S&P *ratings* criteria as your 'loan-level' DSCR authority. That's the same error you claim to have fixed. And S&P doesn't even publish LLCR or PLCR. I'm now checking every number in here."
- **~12 min:** Reserves. "Your DSRA only 'releases at maturity.' Where does it get *drawn* when coverage falls short? A reserve that can't be drawn isn't a reserve. Your negative-CFADS periods will show shortfalls the reserve should have cured — that's a model that overstates default frequency. Model-governance finding under OCC Bulletin 2011-12 / SR 11-7."
- **~22 min:** Breach labels. "'Mechanical test result based on user-supplied inputs' — the debt-service figure that produced this 0.82x isn't user-supplied, your engine computed it. The label is inaccurate, which is worse than no label."

### Counterparty Litigation Counsel (30 min)
- **~6 min:** "Your expert's tool cites the LSTA Model Credit Agreement Provisions as the source for its Excess Cash Flow and cure definitions. The MCAPs don't contain ECF or cure terms — those are negotiated deal terms, deliberately excluded from the form. Your expert's 'authority' doesn't say what he claims it says."
- **~14 min:** "And the MCAPs are for broadly-syndicated *corporate* loans. This is a CRE deal. Your expert applied a corporate-leveraged-loan convention to a real-estate mortgage waterfall and cited a June 2025 'edition' that doesn't exist — the June 2025 document is a *draft*."
- **~24 min:** "Your tool labeled my client's loan an 'event of default' and 'accelerated' it. A tool can't declare an event of default — that's a determination for the agent and lenders under the credit agreement. Calling it 'mechanical' doesn't change that your expert's exhibit states a legal conclusion."

### Senior Project Finance MD (30 min)
- **Immediately:** "Day-count's finally ACT/360 — good, that was the obvious one last time. But you still cite S&P's *ratings* framework for LLCR and PLCR. S&P doesn't size loans; banks do, and S&P doesn't even use LLCR/PLCR. Cite a lender source or own it as your own convention."
- **~7 min:** "How do you compute LLCR with no discount rate in the methodology? You can't. And PLCR needs a cash-flow tail past debt maturity — where does that come from in a period table that ends at maturity?"
- **~15 min:** "You scoped out construction but you accrue interest from the close date and fund the IRA at close. On a construction deal that means the model eats interest with no revenue and no IRA drawdown — it'll throw a default in every construction period. Either model construction interest or start the clock at operations. Right now it's neither."
- **~23 min:** "For a PF deal there's basically no growth capex, so your 'permitted capex = growth only' term is ~zero and fine — but for the CRE deals you also cover, NOI is *before* capex. You never define CFADS for CRE. Half your market gets the sweep wrong."

---

*Audit basis: resolved methodology commit 9875f44 (`methodology-review`). External facts (LSTA MCAP scope/editions, S&P PF criteria name/coverage/level, MBA publication scope) verified via web search July 2026. No code reviewed — methodology-only per working principle #1.*

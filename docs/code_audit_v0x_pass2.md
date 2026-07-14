# waterfall-py v0.x — Code Audit, Pass 2 (hostile re-review)

**Branch:** `audit/v0x-code-2`  **Base under review:** `ad5e0ab` (`feat/v0x-core`)
**Date:** 2026-07-14  **Reviewer stance:** hostile — fixes verified against the CODE
and the amended `docs/methodology.md`, not against the fix session's changelog.

---

## VERDICT: **NO-GO**

GO requires **0 CRITICAL and 0 HIGH**. This pass finds **1 HIGH** (a mis-rated
"deferred LOW", L3, escalated per the audit brief). Every prior C1/H1–H4/M1–M3/
L1/L2/L5 finding is genuinely resolved, and L4 is correctly LOW. The blocker is
isolated and has a contained fix direction, but the code is **not cleared to ship**
until L3 is fixed and a regression test pins it.

| Tier | Count | Items |
|------|-------|-------|
| CRITICAL | 0 | — |
| HIGH | 1 | **L3 (escalated)** — facility draw leaks into ECF / equity; commitment uncapped |
| MEDIUM | 0 | — |
| LOW | 1 | L4 — close tie-out no-op when `project_cost` omitted (confirmed by-design) |
| CLEAN | 12 | C1, H1, H2, H3, H4, M1, M2, M3, L1, L2, L5, methodology drift |

---

## Process guards

- Ran under `PYTHONDONTWRITEBYTECODE=1`; cleared `__pycache__` / `*.pyc` between
  every iteration (including between each mutation probe).
- **Python 3.9.12: `191 passed`.** **Python 3.12: `191 passed`** (fresh venv; the
  only initial miss, `test_export.py`, was a missing `pandas`/`openpyxl` in the
  bare venv — an environment gap, not a code defect; installed and re-ran to 191).
- Working tree clean after all mutation probes (each reverted via `git checkout`).

---

## HIGH

### H-NEW / L3 (escalated) — facility draw inflates ECF and leaks to equity; commitment uncapped
**Files:** `waterfall/models/waterfall.py:88`, `:197`, `:216–245`;
`waterfall/models/tranches.py:` `TrancheState.draw` (no commitment cap);
`waterfall/data/schema.py:` `Tranche.commitment` (validated but never enforced).

**Issue.** A facility/delayed-draw draw is a **non-CFADS financing source**, but the
engine folds it straight into the operating cash pool before ECF is derived:

- `waterfall.py:88` `cash += facility_draw` (top of the period, no earmarked use).
- `waterfall.py:197` `ecf_base = max(cash, 0.0)` — the sweep base is taken from that
  same `cash`, so **un-consumed drawn cash inflates ECF** and is swept, and/or falls
  through steps 6–7 to **equity distribution**.
- `TrancheState.draw()` adds to balance with **no check against `commitment`**.

**Reproduced (live, 3.9):**

- **L3a — leak to equity (no sweep).** Senior 5M bullet + Revolver (`is_facility`,
  `commitment=2M`) + equity; flat CFADS 400k; `facility_draws=[1_000_000, 0…]`.
  Operating residual after debt service = 400k − 250k senior int − 50k revolver int
  = **100k**. Actual `equity_distribution` at t0 = **1,100,000**, while the revolver
  balance stays at **1,000,001 outstanding**. The entire **1,000,000 of borrowed
  debt proceeds was distributed to equity** while its own debt remains unpaid.
- **L3b — swept to prepay other debt (with sweep).** Same deal + 100% sweep: the
  1M draw pushes `sweep_amount` to **1,100,000**, prepaying the *other* senior term
  loan (916,666) and the revolver (183,333) from drawn cash.
- **L3c — uncapped commitment.** `TrancheState(rev).draw(5_000_000)` against a
  `commitment=2_000_000` succeeds; resulting balance 5,000,001. No cap.

**Why it matters.** This is a cash-model correctness defect, not cosmetics. The
methodology defines **ECF ≡ cash remaining after steps 1–4 of the *operating* ladder**
(`methodology.md:82`, sweep.py docstring) and states "CFADS stays operating-only;
every non-CFADS source is recorded separately" (`waterfall.py:16–18`). Financing
proceeds reaching the ECF base violates that contract. Distributing borrowed money to
equity while the drawing facility is still outstanding inverts the capital structure.

**It is invisible to the six assertions.** `assert_cash_conservation` still ties out
(the draw is a recorded *source* of 1M; the distribution is a *use* of 1.1M — sources
= uses). This is exactly the H4 failure mode: an identity that balances for *any*
allocation. No existing test catches it — `test_integration.py::test_revolver_draw_is_a_non_cfads_source`
only asserts `facility_draws == 500_000` and CFADS purity, never that the draw is
kept out of ECF/equity.

**Fix direction.**
1. Keep the facility draw out of the ECF/step-6–7 base: derive the sweep base from
   **CFADS-origin residual only** (e.g. cap `ecf_base` at the operating cash actually
   remaining, tracking the drawn amount as a separate liquidity bucket that can fund
   a shortfall but is never swept or distributed), or apply the draw only against a
   designated use rather than the general `cash` pool.
2. Enforce `commitment`: `TrancheState.draw()` must cap the draw at undrawn
   commitment (raise `InvalidInputError` or clamp) so cumulative draws ≤ `commitment`.
3. Add a concrete regression test: a facility draw with modest CFADS must leave
   `equity_distribution` and `sweep_amount` unchanged from the no-draw case, and a
   draw exceeding `commitment` must be rejected/clamped.

---

## LOW

### L4 — close source/use tie-out is a no-op when `project_cost` omitted — **confirmed by-design**
**File:** `waterfall/models/waterfall.py:483–493` (`_close_source_use`).

When `deal.project_cost is None`, `uses := sources`, so
`assert_source_use_close(sources, uses)` cannot fail. Verified this is the **close /
uses-of-funds** tie-out only (a t=0 capitalization check), and is genuinely optional
per methodology ("ties out trivially when no uses-of-funds supplied"). It does **not**
gate the per-period `assert_cash_conservation`, which runs every period regardless
and would catch a real flow imbalance. When `project_cost` *is* supplied the check is
live (`uses = project_cost + reserve_open`) and fails on mismatch. Cannot mask a real
source/use imbalance. **Correctly rated LOW.**

---

## CLEAN — prior findings verified genuinely resolved

### C1 (was CRITICAL) — trap retires all debt → residual to equity, no crash
`waterfall.py:236–245`. Reproduced the audit's exact repro (vanilla senior-bullet PF,
LLCR trap active at t2 while CFADS still 2.0M, forced 100% sweep retires the whole
1.5M senior). `run()` does **not** raise `WaterfallImbalanceError`; residual
(2,000,000 − 75,000 int − 1,500,000) = **425,000 flows to step-7 equity**; ending
senior balance 0; **cash-conservation holds every period**. Matches amended
methodology `methodology.md:84,86` (trap moot once all debt retired → residual to
equity, mirroring the proceeds path). ✔

### H1 — prepayment re-amortization
`tranches.py` `apply_prepayment`/`_reamortize`; `schema.py` `recompute_on_prepayment:
bool = True`. Default **re-amortizes** over the remaining term; the
`recompute_on_prepayment=False` knob keeps the installment. Independently verified
the changelog's figures: 1M / 4-period fully-amortizing, prepay 400k at t0 →
re-amort schedule `[200k, 200k, 200k]` vs keep-installment `[250k, 250k, 250k]`. ✔

### H2 — LLCR vs PLCR distinct horizons
`waterfall.py:426–449`, `covenants.py` `llcr`/`plcr`. LLCR horizon = loan maturity
(`llcr_end = max senior term`), PLCR horizon = `project_life_periods` (PF-only, now
live). On maturity=4 < project life=8 with flat CFADS: **LLCR = `performance`
(breach), PLCR = `pass`** — distinct values, distinct CFADS slices. PF-only PLCR
enforced (`schema` raises if `project_life_periods` missing on PF PLCR; CRE → n/a). ✔

### H3 — sweep seniority (senior-first, never pari-passu)
`waterfall.py:355–408` (`_apply_prepayment` iterates senior group, then mezz group).
100%-sweep case (senior 3M + mezz 1M): t0 sweep 1,750,000 → **all to senior, mezz
principal 0** while senior outstanding; mezz first touched at t1 only after senior is
fully retired. Same strict order on the proceeds path. ✔

### H4 (test quality) — the key one: all 5 mutation probes now caught
Independently re-ran each probe (mutate → `pytest` → revert), bytecode cleared each
time:

| Probe | Mutation | Result |
|-------|----------|--------|
| cash-trap force / no-leak | `apply_sweep`: drop the `1.0 if cash_trap` force | `test_cash_trap.py` → **2 failed** |
| step-6b reserve top-up | `discretionary_top_up` → return 0 | `test_concrete_ladder.py` → **2 failed** |
| step-3 replenishment | `replenish` → fund 0 | `test_concrete_ladder.py` → **2 failed** |
| DSCR denominator | `dscr` → always `senior_ds + mezz_ds` | `test_concrete_ladder.py` → **2 failed** |
| LLCR/PLCR horizon | PLCR uses `llcr_end` | `test_coverage_horizons.py` → **2 failed** |

Every probe fails ≥1 test — no surviving mutant. The new `test_concrete_ladder.py`
tests pin **concrete per-step dollars** (senior/mezz interest & principal, sweep,
each reserve movement, 6a/6b/6c, equity distribution, DSCR magnitude *and*
denominator inequality) for surplus / DSRA-draw+replenish / step-6b-topup deals, run
for both PF and CRE — not merely "runs + identity ties." ✔

### M1 — step-6b discretionary top-up is live
`waterfall.py:217–229`, `reserves.py` `discretionary_top_up`/`topup_room`. Probe 2
proves it is executed (disabling it breaks `test_concrete_ladder` Deal F); concrete
pins: capex 100k → +90k (per-period cap) → +60k (to 250k target) → 0. ✔

### M2 — floating / step-up rejected, methodology defers them (no contract conflict)
`schema.py` `_OUT_OF_SCOPE_RATES` raises `UnsupportedFeatureError` for `floating` and
`step_up` (verified live). `methodology.md:37,215` list both as **Deferred to v0.1**
with explicit "v0.x rejects … with `UnsupportedFeatureError` (fail-loud)". No residual
"supported" claim for floating/step-up (line 24's "floating-rate inputs modeled at
index reset" sits inside the hedge-accounting scope-out, not a support claim). ✔

### M3 — actions pinned to commit SHAs; pypi-publish repinned to 76f52bc
`gh api` confirms `pypa/gh-action-pypi-publish@76f52bc884231f62b9a034ebfe128415bbaabdfc`
resolves as a real **commit** (v1.12.4). All other action pins
(checkout `11bd719…`, setup-python `0b93645…`, upload-artifact `6f51ac0…`,
download-artifact `fa0a91b…`) also resolve as commits. `release.yml` uses OIDC
Trusted Publishing (`id-token: write`, `environment: pypi`), tag-version guard,
build → wheel-smoke → publish. ✔

### L1 — dead `sweep.ecf()` removed
No `def ecf` / `.ecf(` anywhere in `waterfall/`. ✔

### L2 — disclaimer literally in `DealResult.limitations`
`report/schema.py:82–83`: `disclaimer` field = `STANDARD_DISCLAIMER`; `LIMITATIONS`
contains it as a literal element. `test_guardrails.py::test_disclaimer_present_in_three_locations`
asserts `STANDARD_DISCLAIMER in result.limitations` (list membership) and passes. ✔

### L5 — `_limitations_doc.md` present
Present at repo root; names itself as one of the required limitation locations. ✔

### Methodology drift — bundled == canonical
`cmp docs/methodology.md waterfall/methodology.md` → identical (byte-for-byte).
`test_packaging.py::test_bundled_methodology_matches_canonical_source` passes. ✔

---

## Regression sweep

The fixes touched `waterfall.py` steps 6–7, tranche re-amortization, sweep priority,
and the reserve 6b top-up. The six validation assertions run in-engine **every
period** and raise on violation; the full matrix (5 period types × PF/CRE in
`test_integration.py` + `test_concrete_ladder.py` + the C1 case in `test_cash_trap.py`)
passes on both interpreters, so cash-conservation, principal trace, interest
reconciliation, reserve roll-forward, capital-account roll-forward, and source/use
close all hold across the fixed paths. **No fix introduced a new contradiction**
(the project's recurring failure mode did not recur here). The one defect found (L3)
is a pre-existing modeling gap in the facility-draw path, not a regression from the
step-6/7 / re-amort / sweep / 6b edits.

---

## Ship gate

**NO-GO.** Do **not** merge, tag, or publish. Fix L3 (keep facility draws out of the
ECF/step-6–7 base; enforce `commitment`), add the regression test described above,
re-run the full suite on 3.9 + 3.12, and re-audit. Ship steps are intentionally
omitted — they apply only on a GO.

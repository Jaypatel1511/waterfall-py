# waterfall-py v0.x — Hostile CODE Audit

**Auditor posture:** hostile second-pass reviewer. The build session did not self-certify.
**Contract:** `docs/methodology.md` (LOCKED, pass-7 GO). Where code and methodology disagree, the methodology wins and the gap is a defect.
**Scope of review:** `waterfall/` source + `tests/`, methodology conformance, test quality (mutation probes), fail-loud discipline, packaging/release hygiene.

## Test baseline

| Interpreter | Result |
|---|---|
| Python 3.9.12 (system) | **172 passed** |
| Python 3.12 (venv, pandas+openpyxl installed) | **172 passed** |

The reported 172 pass on both interpreters is confirmed. (3.12 has no system pytest; a venv with `pandas`/`openpyxl` was required — no code defect, just a runner dependency.)

> **Bytecode-cache caveat (methodology note for future audits):** running mutation probes with `git checkout` reverts leaves stale `__pycache__/*.pyc` that Python may re-serve after the source is restored, silently poisoning later runs. All mutation results below were re-run with `PYTHONDONTWRITEBYTECODE=1` and `__pycache__` cleared between every iteration. Verdicts from a naive apply/revert loop are **not** trustworthy.

---

## VERDICT: **NO-GO**

**1 CRITICAL, 3 HIGH (code) + 1 HIGH (test-coverage), 3 MEDIUM, 5 LOW.** GO requires 0 CRITICAL and 0 HIGH.

---

## CRITICAL

### C1 — Engine crashes (`WaterfallImbalanceError`) on a valid PF deal: trapped operating cash has no ladder destination once debt is retired
- **Where:** `waterfall/models/waterfall.py:196-217` (step-5 sweep + step-6/7 gate) and `:252` (`assert_cash_conservation`).
- **Issue:** Under an active cash-trap the step-5 sweep is forced to 100% (`apply_sweep(..., cash_trap=True)`), but `_apply_prepayment` caps the swept amount at the **outstanding debt balance**. When residual operating cash exceeds remaining debt (loan nearly/fully retired, or no sweep leaves a target), the leftover is **not swept** (no debt left to absorb it) and **not distributed** (`if not cash_trap and cash > 1e-12` at `:213` is skipped under the trap). The leftover is never added to the ledger as a use, so `total_sources > total_uses` and the mandatory cash-conservation assertion raises — the engine produces **no output** for a well-formed deal.
- **Reproduction (vanilla PF deal, no exotic inputs):**
  ```python
  Deal(deal_type="PF",
       tranches=[Tranche("Term A","senior",5_000_000,coupon=0.06,amort_type="bullet",term_periods=4),
                 Tranche("Eq","equity",1_000_000)],
       cfads_stream=[1_000_000]*8,
       covenants=[CovenantConfig(metric="LLCR",trap=1.0), CovenantConfig(metric="PLCR",trap=1.0)],
       ... )  # -> WaterfallImbalanceError: period 7 sources 1,000,000 != uses 241,770 (diff 758,230)
  ```
  Instrumented per-period trace confirmed: at period 7 the LLCR/PLCR covenants are in `trap` (future-CFADS PV shrinks to ~0 at end of stream → coverage 0 → breach), the forced 100% sweep retires the last ~238k of senior, and the remaining **~758k of CFADS is dropped on the floor**. LLCR/PLCR covenants are *standard* for project finance, so this is reachable by ordinary use, not a contrived edge.
- **Why it matters:** For a "defensible numeric output" tool, hard-failing on a standard PF-with-coverage-covenant deal is worse than a wrong number — there is no output at all. The methodology's cash-trap rule (line 86, "trapped cash prepays senior debt at step 5") has no defined behavior once senior is retired; its *proceeds-path* sibling (line 88) explicitly says a residual arising after full debt retirement flows to equity — but the operating ladder has no equivalent escape hatch.
- **Fix direction:** When a trap is active and the forced sweep cannot place all residual (debt exhausted), route the un-placeable residual to a defined destination that keeps the ledger total — hold it as a trapped-cash balance (carried forward) or, once **all** debt is retired, release to equity in parallel with the proceeds-path rule at line 88. Add an integration test that drives trap + full retirement and asserts the identity holds with a concrete residual destination.

---

## HIGH

### H1 — Prepayment re-amortization: methodology default is unimplemented *and* not configurable (the flagged suspected defect, confirmed and worse)
- **Where:** `waterfall/models/tranches.py:9-11` (docstring admits "no re-amortization"), `:91` (`build_schedule` runs once in `TrancheState.__init__`), `:119-121` (`scheduled_principal_due` caps installment at balance); `waterfall/data/schema.py` `Tranche` has no `recompute_on_prepayment` field.
- **Methodology (LOCKED, line 51):** "Recompute on prepayment: configurable; **default re-amortize** over remaining term."
- **Issue:** The schedule is built once and never rebuilt after a sweep/prepayment. Verified empirically: a 1,000,000 level-amortizing loan (250k/period) prepaid 400k keeps scheduled installments at **250k** for the remaining periods (loan retires early) instead of **re-amortizing to ~200k/period** over the remaining term. There is no config knob — the "configurable" half of the LOCKED decision is also absent, so a user cannot even opt into the specified default.
- **Why it matters:** Higher scheduled principal in the interim ⇒ higher scheduled senior debt service ⇒ **lower DSCR** than the methodology's re-amortized schedule ⇒ manufactures covenant breaches / cash-traps that would not exist under the LOCKED behavior. Directly corrupts the primary covenant outputs. This is a code-vs-LOCKED conflict, not a permissible simplification.
- **Fix direction:** Add `recompute_on_prepayment: bool = True`; on any balance-reducing movement (sweep/proceeds/prepay) rebuild the remaining schedule over the remaining term (level-principal or mortgage-constant per `amort_type`). Test the re-amortized installment stream against hand-computed numbers.

### H2 — LLCR and PLCR use the wrong horizon; the two metrics collapse to one; `project_life_periods` is a dead field
- **Where:** `waterfall/models/waterfall.py:377` (`future = deal.cfads_stream[t+1:]`), `:389` (`llcr(future, …)`), `:391` (`plcr(future, …)`); `waterfall/data/schema.py:236` (`project_life_periods` defined, **never read anywhere**).
- **Methodology (LOCKED, lines 96-97):** LLCR = PV(CFADS **to loan maturity**) ÷ senior balance; PLCR = PV(CFADS **to end of project life**) ÷ senior balance, horizon "extends beyond loan maturity."
- **Issue:** Both LLCR and PLCR are handed the **identical** slice — the entire remaining CFADS stream — differing only by the CRE→n/a gate in `plcr`. LLCR therefore includes CFADS **past loan maturity** in its numerator (overstates coverage, can mask a real breach); PLCR ignores `project_life_periods` entirely (the field is dead). The whole reason both metrics exist — different horizons — is not implemented.
- **Why it matters:** Silently wrong covenant numbers on the exact defensible-output metrics the methodology is most protective of. Confirmed untested (mutation M13 truncating the horizon **survived** the suite).
- **Fix direction:** Truncate LLCR's `future` at the senior loan-maturity period; drive PLCR's horizon from `project_life_periods` (raise `InvalidInputError` if a PLCR covenant is present without it). Add tests where loan maturity < project life and assert LLCR ≠ PLCR with hand-computed PVs.

### H3 — ECF sweep prepays mezzanine pro-rata; proceeds ignore priority order — seniority is not respected in prepayment allocation
- **Where:** `waterfall/models/waterfall.py:202` (`_apply_prepayment(senior_states + mezz_states, swept, "sweep", …)`), `:236` (same for proceeds), `:327-346` (`_apply_prepayment` splits **pro-rata by balance across all passed tranches**, no seniority tiering).
- **Methodology:** Step 5 (line 82) — the mandatory ECF sweep applies "to **senior** prepayment." Separate proceeds path (line 88) — "applied to outstanding debt **in priority order**." "Senior pro-rata" (line 116) means pro-rata *among senior tranches*, not across senior + mezz.
- **Issue:** Verified empirically: with a 10M senior / 2M mezz stack and a 100% sweep, period-0 sweep prepaid **Mezz by ~299,630** alongside senior — mezzanine is retired pari-passu with senior out of the ECF sweep. Event/reserve-release proceeds are likewise split pro-rata across senior+mezz rather than senior-first.
- **Why it matters:** Understates mezz balance and over-credits it; changes leverage, DSCR-total, LLCR/PLCR denominators and the whole downstream schedule. Violates the foundational seniority principle of a debt waterfall.
- **Fix direction:** Route the mandatory sweep to senior tranches only (pro-rata within the senior group); apply proceeds strictly by seniority (senior group exhausted before mezz). Expose the configurable application order the methodology allows, but default to senior-first. Add tests asserting mezz balance is untouched by an ECF sweep while senior debt remains.

### H4 — Test-coverage: plausible mutations to core logic survive the suite (see Test-Quality subsection)
Per the audit rubric, a plausible mutation that survives is a HIGH test-coverage finding. **Five survived** (cash-trap force/no-leak, reserve step-6b term, step-3 replenishment, engine DSCR denominator, LLCR/PLCR horizon). The integration suite checks *only* "runs without raising + the cash-conservation identity ties out + CFADS purity" — and the identity ties out for **any** allocation of cash across steps, so it cannot detect a mis-allocation *within* the ladder. No integration test pins a single concrete waterfall dollar value (senior interest, principal, sweep split, distribution, DSCR magnitude). Details and table below.

---

## MEDIUM

### M1 — Junior uses 6a/6b/6c collapsed to 6c; no basket caps; not disclosed as a limitation
- **Where:** `waterfall/models/waterfall.py:211-217` (`junior` dict; `equity_distribution = cash` routes **all** retained ECF to distributions), `:214` comment "6a/6b unmodeled in v0.x"; `waterfall/models/reserves.py:64` (`top_up` defined but never called).
- **Methodology (LOCKED, line 83):** step 6 is an ordered sub-ladder 6a growth capex → 6b discretionary reserve top-ups → 6c distributions, **each with a configurable cap**.
- **Issue:** All non-trap retained cash goes straight to equity distribution with no growth-capex bucket, no discretionary reserve top-up, and no distribution basket cap. The `junior_uses` schema column always reports `{growth_capex:0, reserve_topups:0, distributions:X}`. The `reserves.top_up` (step-6b) mechanism is dead. This scope reduction is **not** listed in the Limitations section (methodology line 199 / `report/schema.py:LIMITATIONS`).
- **Fix direction:** Either implement 6a/6b with caps, or (if scoping out for v0.x) add an explicit limitation line, remove the dead `top_up`, and drop the always-zero schema sub-keys so the output does not imply a modeled breakdown.

### M2 — Floating / step-up / default-rate interest and the SIFMA fixing calendar are accepted but silently unimplemented
- **Where:** `waterfall/data/schema.py:36` (`RATE_TYPES` includes `floating`, `step_up`), `:231` (`sofr_calendar` default), `:109` (rate_type validated); `waterfall/models/tranches.py:103-105` (`accrue_interest` uses `self.tranche.coupon` unconditionally); `waterfall/models/dates.py:174` (`adjust`) and the SIFMA calendar are **never called by the engine**.
- **Methodology (LOCKED, Interest Mechanics):** floating (index+spread, caps/floors), step-up, default-rate accrual; SOFR fixings + lookbacks on the SIFMA calendar; payment dates on the Fed calendar under Modified Following.
- **Issue:** A tranche with `rate_type="floating"` (or `step_up`) is accepted without error and modeled as a **fixed coupon** — the rate_type is ignored, no index reset, no caps/floors, no default-rate step, no SOFR fixing. `dates.adjust` and the SIFMA calendar exist and are unit-tested but are wired into nothing; the engine emits only nominal accrual dates. This is a *silent* divergence (worse than a fail-loud `UnsupportedFeatureError`).
- **Fix direction:** Implement floating/step-up/default-rate accrual and SOFR fixing on the SIFMA calendar, **or** reject those `rate_type`s with `UnsupportedFeatureError` in v0.x and document the SIFMA/`adjust` machinery as forward-looking. Do not accept-and-ignore.

### M3 — Release pipeline pins `pypa/gh-action-pypi-publish` to the **annotated-tag object SHA**, not a commit SHA → publish step will fail to resolve
- **Where:** `.github/workflows/release.yml` publish job — `pypa/gh-action-pypi-publish@7f25271a4aa483500f742f9492b2ab5648d61011  # v1.12.4`.
- **Issue:** Verified against the GitHub API: `7f25271a…` is the **tag object** SHA (`git/ref/tags/v1.12.4 → object.type == "tag"`); dereferencing it yields the real commit `76f52bc884231f62b9a034ebfe128415bbaabdfc`. `GET /commits/7f25271a…` returns **422 "No commit found."** GitHub Actions requires `uses: …@<sha>` to reference a **commit** SHA; an annotated-tag object SHA does not resolve and the publish step errors at runtime. The other four pinned actions (`checkout`, `setup-python`, `upload-artifact`, `download-artifact`) correctly pin to commit SHAs and resolve. This also violates the "all actions SHA-pinned" release principle (a non-commit SHA is not a valid pin).
- **Why it matters:** The publish job is non-functional as written; the first `v*` tag push would fail at the PyPI step. Fails safe (nothing bad ships), but the release is broken.
- **Fix direction:** Repin to the commit SHA `76f52bc884231f62b9a034ebfe128415bbaabdfc  # v1.12.4`.

---

## LOW

- **L1 — Dead `sweep.ecf()`.** `waterfall/models/sweep.py:17-20` defines the ECF formula, but the orchestrator uses the physical residual (`ecf_base = max(cash, 0.0)`, `waterfall.py:197`) instead. The function is unit-tested but unreachable from `run()`. Either use it (single source of truth) or delete it; a future edit to one path won't be caught by the other.
- **L2 — Disclaimer not literally in `DealResult.limitations`.** Methodology line 196 names three disclaimer locations including `DealResult.limitations`; `report/schema.py:LIMITATIONS` carries limitation strings, not the `STANDARD_DISCLAIMER`. The disclaimer does appear in `interpretation`, the rendered report, and the `disclaimer` attribute (three surfaces), and the test (`test_guardrails.py`) checks those — but the specific named location is not literally satisfied.
- **L3 — Facility draw can leak into ECF / distribution and bypasses `commitment`.** `waterfall.py:87-93` adds a scheduled facility draw to `cash` with no cap against `Tranche.commitment`; unconsumed drawn cash flows into the ECF sweep or equity distribution rather than funding a specific use. Edge, but a revolver draw that isn't consumed is economically mis-modeled.
- **L4 — Close source/use tie-out is a no-op when `project_cost` is omitted.** `waterfall.py:428-431` sets `uses = sources` when no uses-of-funds are supplied, so `assert_source_use_close` can never fail in that branch. Acceptable (uses-of-funds optional) but the tie-out only bites when `project_cost` is given.
- **L5 — `_limitations_doc.md` absent.** Methodology line 199 names `_limitations_doc.md` as one of the 3+ required limitation locations; the file does not exist (limitations live in methodology.md, `DealResult.limitations`, and every rendered report — 3 places, but not the named file).

---

## CLEAN (verified, not merely present)

- **Dual-import shim.** `waterfall`, `waterfall_py`, `waterfallpy` are the same package object; submodules (`…models.waterfall`, `…data.schema`) and classes (`Deal`, `Tranche`) are identical across all three spellings — verified by identity checks, so `isinstance` cannot break. (`test_packaging.py` + independent verification.)
- **Methodology bundling.** `get_methodology_path()` resolves via `importlib.resources` to `waterfall/methodology.md`; byte-identical to `docs/methodology.md` (sha256 match); the drift test (`test_bundled_methodology_matches_canonical_source`) compares full bytes and is meaningful.
- **EOM vs Modified Following resolution.** Accrual period-ends are nominal EOM-snapped (used for day-count), payment/observation dates are separately business-day-adjusted via `adjust`. The 2024-03-31 (Sunday) case resolves correctly: nominal accrual end stays 2024-03-31; Modified-Following payment date rolls **back** to Fri 2024-03-29 on the Fed calendar (Good Friday is not a Fed holiday) and to Thu 2024-03-28 on SIFMA (Good Friday closed). Day-count and payment dating each correct; two calendars kept distinct.
- **CFADS purity.** Cures, facility draws, reserve draws/releases, and event proceeds are added to `cash`, never to `cfads`; reported `cfads` equals the raw input every period (verified across cure/revolver/DSRA-draw scenarios). Mutation M17 (using gross CFADS as the ECF base) is caught.
- **DSCR div-by-zero → n/a.** `covenants.dscr`/`llcr`/`plcr`/`ltv`/`debt_yield` return `NaN` when the denominator is ≤ 0; `evaluate` maps NaN → "n/a" (not tested). Never `inf`, `0`, or a raise.
- **Six assertions each fire on corrupted input** with the specific typed exception (`test_assertions.py`). No silent `except: pass`, no swallow-to-empty, no hardcoded fallback records; absent financials are `NaN`, never `0.0`.
- **Interest-recon ↔ principal-trace facility-draw seam.** `opening` is captured pre-draw (principal trace: `opening + draws − … = closing`); `accrual_balance` is captured post-draw (interest accrues on the drawn balance). Both assertions run every period (`waterfall.py:253-259`) and hold simultaneously; neither is loosened.
- **General cash-conservation is ledger-enumerated, not a fixed list.** `PeriodLedger.total_sources/total_uses` sum over dynamically-appended entries (`audit/log.py:38-42`); the identity is structurally drift-proof as the methodology requires.
- **Out-of-scope inputs raise `UnsupportedFeatureError`** (b-piece, preferred equity, multi-currency, construction draw, OID, sculpted-to-DSCR, ACT/ACT) — all subclass `WaterfallError`.
- **CI/release scaffolding (mostly).** CI matrix is 3.9–3.12; the wheel job asserts methodology bundled + no stray test files + shims present; `release.yml` is tag-triggered (`tags: v*`, never on branch push), version-guarded via `tomllib`, OIDC Trusted Publishing, 4/5 actions correctly commit-SHA-pinned (see M3 for the 5th); CHANGELOG present.

---

## Test-Quality subsection — mutation-probe results

Probes run with bytecode disabled and `__pycache__` cleared per iteration (baseline 172 pass each run). "SURVIVED" = the full suite still passed with the defect injected.

| # | Mutation (target) | Result | Meaning |
|---|---|---|---|
| S | `ACT/360 → ACT/365` in `dates.day_count_fraction` | CAUGHT (`test_act_360`) | harness works; day-count pinned |
| M1 | drop `+ topups` (step-6b) from `assert_reserve_roll_forward` | **SURVIVED** | the step-6b term is never exercised with a nonzero value (mechanism unmodeled, corruption test uses `topups=0`) |
| M2 | engine `cash_trap = False` (disable the 100% force / no-leak-to-equity) | **SURVIVED** | the flagship cash-trap guarantee is untested end-to-end; only `apply_sweep()` is unit-tested in isolation |
| M12 | engine reported DSCR denominator `senior → total` | **SURVIVED** | no integration test pins the reported `p.dscr` to the senior denominator (currently correct, but unprotected) |
| M13 | LLCR/PLCR horizon truncated to one future period | **SURVIVED** | the coverage-metric horizon is untested (compounds H2) |
| M18 | skip step-3 required reserve replenishment | **SURVIVED** | required DSRA funding at step 3 is not verified by any test |
| M14 | disable the DSRA shortfall draw | CAUGHT (`test_dsra_draw_absorbs_shortfall`) | DSRA-draw path is covered |
| M17 | ECF base = gross CFADS instead of the step-1..4 residual | CAUGHT (28 fails) | gross mis-scoping breaks the identity |
| M5 | swap `swept`/`retained` at the sweep call site | CAUGHT | sweep-vs-retained split is covered (via `test_sweep` + downstream) |

**Root cause of the survivors:** the integration tests assert only (a) no exception, (b) `total_sources == total_uses` per period, and (c) CFADS purity. The cash-conservation identity ties out for **any** split of cash among the ladder steps, so it cannot detect a mis-allocation *inside* the ladder (wrong step gets the money, wrong tranche is prepaid, wrong denominator, wrong horizon). No integration test pins a concrete waterfall figure. The five validation-assertion corruption tests are good (each fires with the right typed exception), and the unit tests pin concrete numbers for individual functions — but the **orchestration layer** (how the pieces are wired) is under-tested.

**Recommended additions:** for each of the five period-type scenarios × CRE/PF, assert hand-computed senior interest, senior/mezz principal, sweep split, distribution, ending balances, and DSCR magnitude; add an engine-level test that a trap zeroes equity distribution and forces 100% sweep (kills M2); add a nonzero-top-up path (kills M1); add a step-3 replenishment assertion (kills M18); add LLCR≠PLCR horizon tests (kills M13, covers H2).

---

## Summary table

| Severity | ID | One-line |
|---|---|---|
| CRITICAL | C1 | Trapped operating cash after debt retirement → spurious `WaterfallImbalanceError`; engine emits no output on a standard PF deal |
| HIGH | H1 | Prepayment re-amortization (methodology default) unimplemented and non-configurable → wrong DSCR/covenants |
| HIGH | H2 | LLCR/PLCR share the wrong horizon; metrics collapse; `project_life_periods` dead → silently wrong coverage |
| HIGH | H3 | ECF sweep prepays mezz pro-rata; proceeds ignore priority order → seniority violated |
| HIGH | H4 | Five plausible mutations survive the suite; orchestration layer under-tested |
| MEDIUM | M1 | Junior 6a/6b/6c collapsed to distributions; no caps; undisclosed |
| MEDIUM | M2 | Floating/step-up/default-rate + SIFMA/payment-dating accepted but silently unimplemented |
| MEDIUM | M3 | pypi-publish action pinned to tag-object SHA, not commit → publish fails |
| LOW | L1 | Dead `sweep.ecf()` |
| LOW | L2 | Disclaimer not literally in `DealResult.limitations` |
| LOW | L3 | Facility draw leaks into ECF; `commitment` uncapped |
| LOW | L4 | Close tie-out no-op when `project_cost` omitted |
| LOW | L5 | `_limitations_doc.md` (named in methodology) absent |

**GO / NO-GO: NO-GO.** Clear on 0 CRITICAL / 0 HIGH; found 1 CRITICAL and 4 HIGH. C1 blocks output on a realistic deal; H1/H2/H3 corrupt the primary covenant/schedule numbers; H4 means the suite would not have caught them. Do not tag/push/publish.

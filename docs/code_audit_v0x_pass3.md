# Code audit — v0.x, pass 3 (hostile re-review of the L3 HIGH closure)

**Branch:** `audit/v0x-code-3`  **Reviewed commit:** `f9e5a4d` (== `main` == `feat/v0x-core`)
**Reviewer stance:** hostile. Verified against the code and the amended methodology, **not** the changelog.
**Process guards:** `PYTHONDONTWRITEBYTECODE=1`, `__pycache__`/`*.pyc` cleared between every mutation
iteration, all mutation runs in an isolated repo copy. Fresh venvs on CPython 3.9.12 and 3.12.13
(pandas/numpy/openpyxl/pytest installed — no defect, env gap only).

---

## Verdict

- **L3 (HIGH) closure — code correctness:** ✅ **GENUINELY CLOSED.** The leak vector is deleted, the
  leak is independently reproduced on the pre-fix code and shown gone, the commitment cap is enforced
  on both sides with no gap, and the regression tests pin concrete dollars. **0 CRIT / 0 HIGH in the
  L3 fix and its blast radius.** No regression, no new leak.
- **Overall ship readiness:** 🚫 **NO-GO** — blocked by **CRIT-1 (release/version collision)**, a
  release-hygiene defect *outside* the L3 code but squarely in the ship path the deliverable asked me
  to validate. The post-publish smoke test uncovered that `waterfall-py 0.1.0` is **already on PyPI
  (uploaded 2026-04-24) with different, older code**, and PyPI versions are immutable. The already-pushed
  `v0.1.0` tag and the release workflow **cannot** deliver the current engine to PyPI.

> Per the rubric ("GO only if 0 CRIT / 0 HIGH"), one CRITICAL in the ship path ⇒ **NO-GO overall.**
> The L3 *code* is correct and cleared; the *release* is not shippable as configured. **Do not push
> the tag / run the release workflow / merge-to-ship until CRIT-1 is fixed.**

---

## CRITICAL

### CRIT-1 — `pyproject.toml:7` / `waterfall/__init__.py:33` — v0.1.0 already published to PyPI; the current engine cannot ship under this version
- **Issue:** The package version is `0.1.0`. PyPI already hosts **`waterfall-py 0.1.0`**, uploaded
  **2026-04-24T16:29:21Z** (`waterfall_py-0.1.0-py3-none-any.whl` + `.tar.gz`). That published artifact
  is an **early, unrelated prototype** — its `Tranche` uses `rate`/`term_years`/`priority`/`is_mezz`/`pik_rate`,
  raises bare `ValueError`, and has **no `Deal`, no `is_facility`/`commitment`, no typed exceptions, no
  bundled methodology, no `audit`/`report` packages**. It is the *same PyPI project* (project Homepage =
  `github.com/Jaypatel1511/waterfall-py`), i.e. Jay's own earlier upload — not a squatter — but the code
  bears no resemblance to the audited `f9e5a4d` engine.
- **Why it blocks the ship:**
  1. **PyPI is immutable.** The publish step (`release.yml:87`, `pypa/gh-action-pypi-publish@v1.12.4`,
     no `skip-existing`) will attempt to upload filename `waterfall_py-0.1.0-*` and PyPI will reject it
     `400 File already exists`. **The publish job fails.** The `verify-version` guard (`release.yml:24`)
     passes (tag `v0.1.0` == pyproject `0.1.0`), so nothing stops the run *before* the doomed upload.
  2. The annotated tag **`v0.1.0` is already created and already pushed to origin** (`git ls-remote --tags
     origin` → `refs/tags/v0.1.0` → deref `f9e5a4d`). So the "tag → push → CI publishes" sequence in the
     deliverable is not a fresh action — it has effectively already been fired and cannot succeed.
  3. **Users get the wrong package today.** `pip install waterfall-py` currently installs the April
     prototype, not the audited engine. There is no way to fix `0.1.0` in place.
- **Fix direction (required before any ship):**
  1. Bump the version — `pyproject.toml:7` **and** `waterfall/__init__.py:33` — to an unused version
     (recommend **`0.2.0`**, since the public API changed completely from the April `0.1.0`; `0.1.1`
     would misrepresent a total rewrite as a patch).
  2. Delete the stale tag locally and on origin (`git tag -d v0.1.0`; `git push origin :refs/tags/v0.1.0`)
     — it points at code that can never publish under that number — and cut a **new** annotated tag
     matching the bumped version.
  3. Re-run the corrected ship sequence (below). Consider adding `skip-existing: false` explicitly and a
     pre-publish "version not already on PyPI" guard to `release.yml` so this fails *loudly at verify-time*
     next time, not at the publish step.

---

## HIGH

None. The L3 fix is correct and complete (see verification below).

---

## MEDIUM

None.

---

## LOW

### LOW-1 — `waterfall/models/tranches.py:210` — `draw()` commitment guard fires even for non-facility tranches; schema only validates the at-close cap for `is_facility`
- `Tranche.__post_init__` (`schema.py:163`) checks `principal ≤ commitment` **only when `is_facility`**,
  but `TrancheState.draw()` caps cumulative draws against `commitment` **regardless** of `is_facility`
  (`_drawn_total` seeded to `principal` at `tranches.py:92`). A non-facility tranche carrying a
  `commitment < principal` would therefore pass schema validation yet have every `draw()` (even `draw(0)`)
  rejected. **Dormant, not live:** the engine no longer calls `draw()` at all (the path is deleted), and
  a non-facility isn't drawn. Cosmetic asymmetry only. *Fix direction:* either reject `commitment` set on
  a non-facility in the schema, or make the schema cap check symmetric with the state-side cap.

### LOW-2 — `tests/test_integration.py:28` — the "revolver" integration scenario funds the facility with a nominal `principal=1.0`
- The reframed funded-at-close scenario gives the Revolver a `$1` opening balance, so it barely exercises
  "funded at close." Adequately compensated: `test_facility_deferred.py` pins the real `2,000,000`
  at-close case with exact-dollar baseline equality. *Fix direction (optional):* fund the integration
  revolver at a material amount for a stronger end-to-end check.

### LOW-3 — `waterfall/models/waterfall.py:90` — `facility_draw = 0.0` local is a dead constant
- It exists only to feed `PeriodResult(facility_draws=facility_draw, …)` at line 300, always `0.0`.
  Harmless and arguably a readable trace of the deferred mechanic; could be inlined as the literal `0.0`.
  No behavioral impact.

---

## CLEAN (verified, no finding)

**L3 leak vector deleted.** `waterfall.py` no longer folds a facility draw into `cash`/`ecf_base`; the
old `:88/:92`-era path (`facility_state.draw(...)`, `cash += facility_draw`, `ledger.add_source(
"facility_draw", …)`) is gone. `cash = cfads` (line 91); `ecf_base = max(cash, 0.0)` (line 194) is
CFADS-origin only. `grep` confirms **no `.draw()` call remains anywhere in `waterfall/`** — the primitive
is now only exercised by tests.

**Independent L3a reproduction.** Same deal params (senior 5M bullet + revolver `commitment=2M` + equity,
flat CFADS 400k, no-sweep so residual → equity), run on the **pre-fix** (`f9e5a4d^`) vs **post-fix** trees:

| | at-close funding only, t0 equity | +1,000,000 mid-life draw at t0, t0 equity |
|---|---|---|
| **pre-fix (`f9e5a4d^`)** | `293,833.33` | `1,278,666.67` — **~984,833 of borrowed cash leaked to equity** |
| **post-fix (`f9e5a4d`)** | `293,833.33` (identical) | **REJECTED** `UnsupportedFeatureError` |

The pre-fix leak (`+draw − extra accrual on the inflated balance`) is exactly the L3 failure; the post-fix
tree rejects the draw at input validation and the at-close-only path is byte-identical to the pre-fix
at-close path — the at-close 2M never touches the operating pool. (The pass-2 write-up's specific
`100,000 → 1,100,000` figures are scenario-param-specific; the *mechanism* — ~1M borrowed dollars reaching
equity — is reproduced exactly.) `test_facility_deferred.py::test_facility_funded_at_close_does_not_leak_to_equity_or_sweep`
independently pins funded-at-close == no-facility baseline with `abs=1e-9` equality on both
`equity_distribution` and `sweep_amount`.

**Mid-life draws rejected, fail-loud, including period 0.** `schema.py:364` rejects `any(x > 0 for x in
facility_draws)` with `UnsupportedFeatureError`; `_validate_period_series` (`schema.py:293`, run first)
rejects negatives with `InvalidInputError` — so **only an all-zero schedule is accepted** (no negative-draw
loophole). Verified: `[…,500_000,…]` and `[1_000_000,0,0,0]` (period 0) both raise; `[0,0,0,0]` runs with
`facility_draws==0` every period. Methodology-faithful: at-close funding is carried by the tranche opening
balance / principal (methodology lines 30, 52, 172, 175, 216), **not** by `facility_draws[0]`; a legitimate
at-close funding path is **not** blocked (proven by the funded-at-close baseline test running cleanly).

**Commitment cap enforced, both sides, no gap.** Schema (`schema.py:158-166`): `commitment` must be
non-negative, and for a facility `principal ≤ commitment`. State (`tranches.py:212-219`): `_drawn_total`
(seeded to the opening `principal`) + further draw must not exceed `commitment + 1e-6` else
`InvalidInputError`; no-commitment facilities stay uncapped by design. The two agree — at-close `principal
≤ commitment` (schema) leaves the state cap's headroom = undrawn commitment, so there is no window between
them. The 5M-against-2M case is rejected **twice over**: at construction (a facility `principal=5M,
commitment=2M` raises in `__post_init__`) and at the primitive (`TrancheState(principal=1).draw(5M)` raises).

**Regression tests are real and concrete.** `test_facility_deferred.py` asserts exact values, not just
"no exception": funded-at-close vs baseline equality on `equity_distribution` **and** `sweep_amount`
(`abs=1e-9`); `st.balance == 1,000,001.0` after an in-cap draw; typed-exception rejections for mid-life
(incl. period 0), over-commitment draw, and over-commitment at-close funding. `test_integration.py`'s
"revolver" scenario is reframed to funded-at-close: the buggy `facility_draws[2]=500_000` contract and the
`periods[2].facility_draws == 500_000` assertion are **deleted**, replaced by "`facility_draws == 0` every
period + CFADS purity."

**`facility_draws` output column = 0 every period — intentional and documented, not a silent hole.** It
remains a live schema/export column (`report/schema.py:56`, `report/export.py`), pinned to 0 by the
principal trace (draws term = 0), and documented at methodology lines 175 & 185 and in the engine/schema
comments. No dangling references to the removed path (`grep` clean apart from the documented `facility_draw
= 0.0` trace and the still-valid column).

---

## Regression sweep

### Test suite — full green on both interpreters
- **CPython 3.9.12:** `198 passed`.  **CPython 3.12.13:** `198 passed`.  (Matches the reported 198.)
- Fresh venvs; `__pycache__` cleared before each run. No failures, no env gaps after installing deps.

### H4 mutation probes — all five re-run independently; **each is now caught** (no coverage regression)
Run in an isolated repo copy, `PYTHONDONTWRITEBYTECODE=1`, cache cleared per iteration. Testbed baseline =
4 pre-existing `test_packaging.py` failures (missing top-level shim modules + methodology path **in the
copy only** — the real tree is 198/198); "caught" = failures **above** that baseline, by the named tests.

| Probe | Mutation | Result | Caught by |
|---|---|---|---|
| **M1** | drop `+ topups` from `assert_reserve_roll_forward` | ✅ CAUGHT (+3) | `test_reserve_roll_forward_counts_the_step6b_topup_term`; `test_step6b_discretionary_topup_concrete[PF,CRE]` |
| **M2** | engine `cash_trap = False` | ✅ CAUGHT (+2) | `test_trap_forces_full_sweep_and_no_leak_while_debt_remains`; `test_c1_trap_retires_all_debt_routes_residual_to_equity` |
| **M12** | reported DSCR denominator `senior → total` | ✅ CAUGHT (+2) | `test_surplus_ladder_concrete[PF,CRE]` |
| **M13** | LLCR/PLCR horizon truncated to one future period | ✅ CAUGHT (+4) | `test_llcr_value_is_bracketed_by_thresholds`; `test_trap_forces_full_sweep_and_no_leak_while_debt_remains` |
| **M18** | skip step-3 required reserve replenishment | ✅ CAUGHT (+2) | `test_dsra_draw_then_step3_replenish_concrete[PF,CRE]` |

All five formerly-surviving mutations (pass-1 H4) are now killed by concrete-value tests. Removing the
facility-draw path did not regress this coverage.

### Six assertions × five period types × CRE/PF + C1 — intact
The six per-period assertions (cash-conservation, interest reconciliation, principal trace, reserve
roll-forward, capital-account, source/use close) run every period across `test_assertions`,
`test_concrete_ladder` (CRE/PF-parametrized), `test_integration` (5 scenarios × CRE/PF), and
`test_cash_trap`. All green under the 198-pass suite. The **C1 trap-retires-all-debt** case
(`test_c1_trap_retires_all_debt_routes_residual_to_equity`) passes and is sensitive (it catches M2).
Removing the facility path did not break the principal trace (draws term is now a constant 0, which the
trace tolerates — `opening + 0 − sched − prepay − sweep = closing`).

### Methodology drift — byte-identical
`waterfall/methodology.md` == `docs/methodology.md` (`cksum` 272712193/43509 both; `diff` empty). Drift
test passes. Amended methodology is internally consistent with the deferral: facilities funded at close,
mid-life draws rejected, commitment cap enforced, `facility_draws` principal-trace term = 0 in v0.x.

### No new contradiction
No dangling reference, dead column, or unsatisfiable assertion from the deletion. `facility_draws` stays a
valid (constant-0) column with an explicit methodology statement. The only residue is the harmless
`facility_draw = 0.0` local (LOW-3).

---

## Remediation & corrected ship sequence

**Do not execute the deliverable's ship sequence as written — it fails at publish (CRIT-1).** The L3 code
is cleared; the release is not. Required order:

1. **Fix CRIT-1 first.** Bump version to `0.2.0` in `pyproject.toml:7` **and** `waterfall/__init__.py:33`.
   Delete the stale tag: `git tag -d v0.1.0 && git push origin :refs/tags/v0.1.0`. (Optionally harden
   `release.yml` with a "not already on PyPI" pre-check.) Commit the bump on `feat/v0x-core`.
2. Merge `feat/v0x-core → main` (currently a fast-forward — `main` already == `feat/v0x-core`).
3. **Annotated** tag the **new** version: `git tag -a v0.2.0 -m "waterfall-py v0.2.0 …"`.
4. Push `main`, then the tag: `git push origin main && git push origin v0.2.0`.
   **The tag push is the one irreversible step** — it triggers OIDC publish to PyPI, and a PyPI upload
   cannot be unpublished/overwritten. Do it only after steps 1–3 are verified.
5. Let CI/OIDC (`release.yml`) build → test-wheel → publish `0.2.0`.
6. **Post-publish PyPI smoke test** in a clean venv from a neutral directory (not the repo cwd, or the
   local tree shadows the wheel — as it did in this audit): `pip install waterfall-py==0.2.0`, then verify
   `waterfall.__version__ == "0.2.0"`, a mid-life `facility_draws` raises `UnsupportedFeatureError`, the
   commitment cap raises `InvalidInputError`, and a basic deal runs with funded-at-close == baseline. (This
   audit ran exactly that battery against the current PyPI artifact; it is how CRIT-1 surfaced.)

Once `0.2.0` is live and the smoke test is green, the engine is shipped and cleared.

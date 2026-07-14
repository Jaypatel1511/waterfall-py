# waterfall-py — Documented Limitations (v0.x)

This file is one of the required limitation locations named in
`docs/methodology.md` ("Limitations — Documented in 3+ Places: methodology.md,
`DealResult.limitations`, every report, `_limitations_doc.md`"). It mirrors
`waterfall.report.schema.LIMITATIONS`, which is attached to every `DealResult`
and rendered into every report.

waterfall-py v0.x is a tight-core mechanical debt-waterfall engine. The following
are explicitly out of scope and are enumerated here so no output implies a
capability the engine does not have:

- No NOI / CFADS projection modeling — CFADS is a user-supplied input.
- No construction-period modeling; the engine's clock starts at operations (period 0).
- Engine does not verify capex classification (maintenance vs. growth) or reserve
  classification (required vs. discretionary) — these are input-preparer responsibilities.
- No tax modeling; no SPV tax-distribution (phantom-income) modeling.
- No derivatives / hedge accounting.
- No equity promote / carried interest (debt waterfall; equity is residual only).
- No CMBS bond-level tranching.
- No A/B note structures or B-piece shortfall mechanics.
- No preferred-equity / quasi-debt tranche.
- No tax credit equity flips.
- No defeasance (yield maintenance only).
- No OID modeling.
- No sculpted-to-DSCR amortization (deferred — requires an iterative solver).
- No ACT/ACT day-count (30/360, ACT/360, ACT/365F only).
- Single-currency only.
- No floating / step-up rate accrual (fixed and PIK only in v0.x; a floating/step-up
  `rate_type` is rejected with `UnsupportedFeatureError`, not silently modeled as fixed).
- No step-6a growth / discretionary capex bucket (requires a growth-capex spend input;
  step-6b discretionary reserve top-ups and step-6c distributions are modeled).

**Standard disclaimer.** Mechanical waterfall computation only. Not a credit
recommendation. CFADS inputs are user-supplied projections, not modeled cash flows.

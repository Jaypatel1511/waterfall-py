# Changelog

All notable changes to `waterfall-py` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project aims to
adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **v0.x tight-core engine** — `waterfall.run(deal)` applies the LOCKED
  period-by-period Waterfall Priority ladder (senior fees → senior debt service
  with DSRA-draw then equity-cure shortfall cover → required reserve funding →
  mezzanine debt service → mandatory ECF sweep, forced to 100% under a cash-trap
  → permitted junior uses → residual to equity) plus a separate proceeds path
  for reserve releases and event proceeds. CFADS stays operating-only.
- Input contract (`waterfall.data.schema`): `Deal`, `Tranche`, `ReserveConfig`,
  `CovenantConfig`, `Fee`, `SweepConfig`, `SweepBand` with required/optional
  validation and out-of-scope rejection (`UnsupportedFeatureError`).
- Dates (`waterfall.models.dates`): 30/360, ACT/360, ACT/365F day-count;
  U.S. Federal Reserve and SIFMA calendars; Modified Following; EOM; period stubs.
- Tranches, reserves, covenants, sweep modules; covenants report **n/a** on a
  zero denominator; three-tier cushion.
- Six built-in validation assertions (source/use tie-out, period
  cash-conservation, principal trace, interest reconciliation, reserve
  roll-forward, capital-account roll-forward), each raising a typed exception.
- Reports (`waterfall.report`): native DataFrame, Excel (openpyxl), JSON, and a
  text report; the standard disclaimer appears in three locations; every breach
  is labeled a mechanical test result.
- Typed exception hierarchy (`waterfall.data.exceptions`): `WaterfallError` base
  with `InvalidInputError`, `UnsupportedFeatureError`, and one typed error per
  validation assertion, plus reserved `ModelConvergenceError`.
- Dual-import shim (WP #6): `import waterfall_py` and `import waterfallpy` resolve
  to the same package as `import waterfall`, including submodules (no duplicate
  module objects).
- Methodology bundled in the wheel; `waterfall.get_methodology_path()` locates it
  via `importlib.resources`. A regression test enforces byte-identity with the
  canonical `docs/methodology.md`.
- CI matrix Python 3.9–3.12 with a clean-wheel / methodology-resolves job;
  SHA-pinned GitHub Actions; tag-triggered OIDC Trusted-Publisher `release.yml`.

[Unreleased]: https://github.com/Jaypatel1511/waterfall-py/compare/main...HEAD

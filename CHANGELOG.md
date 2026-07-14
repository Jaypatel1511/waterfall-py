# Changelog

All notable changes to `waterfall-py` are documented here. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) and the project aims to
adhere to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Typed exception hierarchy (`waterfall.data.exceptions`): `WaterfallError` base
  with `InvalidInputError`, `UnsupportedFeatureError`, and one typed error per
  validation assertion (`SourceUseImbalanceError`, `WaterfallImbalanceError`,
  `PrincipalTraceError`, `InterestReconciliationError`, `ReserveRollForwardError`,
  `CapitalAccountError`) plus reserved `ModelConvergenceError`.
- Dual-import shim (WP #6): `import waterfall_py` and `import waterfallpy` resolve
  to the same package as `import waterfall`, including submodules (no duplicate
  module objects).
- Methodology bundled in the wheel; `waterfall.get_methodology_path()` locates it
  via `importlib.resources`. A regression test enforces byte-identity with the
  canonical `docs/methodology.md`.

[Unreleased]: https://github.com/Jaypatel1511/waterfall-py/compare/main...HEAD

"""Packaging guarantees that must hold from day 1.

- Dual-import shim: ``waterfall_py`` and ``waterfallpy`` both resolve to the
  SAME package object as ``waterfall`` (methodology Release Process, WP #6).
- Methodology is bundled and locatable via ``get_methodology_path()``
  (importlib.resources), and the bundled copy does not drift from the canonical
  ``docs/methodology.md`` source of truth.
"""
import os

import waterfall


def test_version_exposed():
    assert isinstance(waterfall.__version__, str)
    assert waterfall.__version__


def test_dual_import_shim_waterfall_py():
    import waterfall_py
    assert waterfall_py is waterfall


def test_dual_import_shim_waterfallpy():
    import waterfallpy
    assert waterfallpy is waterfall


def test_dual_import_reaches_submodules():
    import waterfall_py.data.exceptions as exc_alias
    from waterfall.data import exceptions as exc_real
    assert exc_alias is exc_real


def test_get_methodology_path_resolves_to_readable_file():
    path = waterfall.get_methodology_path()
    assert os.path.isfile(path)
    text = open(path, encoding="utf-8").read()
    assert "waterfall-py: Methodology" in text
    assert "Waterfall Priority" in text


def test_bundled_methodology_matches_canonical_source():
    """The wheel-bundled copy must be byte-identical to docs/methodology.md."""
    bundled = open(waterfall.get_methodology_path(), encoding="utf-8").read()
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    canonical = open(
        os.path.join(repo_root, "docs", "methodology.md"), encoding="utf-8"
    ).read()
    assert bundled == canonical, "bundled methodology drifted from docs/methodology.md"

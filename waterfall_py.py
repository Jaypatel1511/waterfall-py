"""Import alias: ``waterfall_py`` -> the ``waterfall`` package (WP #6).

``import waterfall_py`` and any ``import waterfall_py.<submodule>`` resolve to the
exact same module objects as ``import waterfall`` / ``import waterfall.<submodule>``.
See :mod:`waterfall._aliasing` for the mechanism.
"""
from waterfall._aliasing import install

install(__name__)

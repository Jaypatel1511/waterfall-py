"""Dual-import aliasing (methodology Release Process, WP #6).

Goal: ``import waterfall_py`` / ``import waterfallpy`` and *any* submodule thereof
resolve to the exact same module objects as ``import waterfall`` — so classes are
never duplicated across spellings (which would silently break ``isinstance``).

Mechanism: a meta-path finder maps every ``<alias>.<suffix>`` name onto the real
``waterfall.<suffix>`` module object. The loader returns that real module from
``create_module``; the import machinery's ``_init_module_attrs`` then clobbers the
real module's ``__spec__`` with the *alias* spec. ``exec_module`` restores the
real identity from a snapshot captured in ``find_spec`` (before any clobber).
Without that restore the real package's ``__spec__`` would point at an alias name
with no ``submodule_search_locations`` and ``importlib.resources.files('waterfall')``
would raise "not a package".
"""
import importlib
import importlib.abc
import importlib.util
import sys

ALIASES = ("waterfall_py", "waterfallpy")
_REAL = "waterfall"

# Identity attributes that _init_module_attrs may overwrite when create_module
# returns a pre-existing module; restored from the snapshot in exec_module.
_IDENTITY_ATTRS = ("__spec__", "__name__", "__loader__", "__package__", "__path__")


def _real_name(alias_name):
    _, _, suffix = alias_name.partition(".")
    return _REAL + ("." + suffix if suffix else "")


class _AliasLoader(importlib.abc.Loader):
    def __init__(self, real_module, snapshot):
        self._real = real_module
        self._snapshot = snapshot

    def create_module(self, spec):
        return self._real

    def exec_module(self, module):
        for attr, value in self._snapshot.items():
            setattr(module, attr, value)


class _AliasFinder(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path=None, target=None):
        root = name.partition(".")[0]
        if root not in ALIASES:
            return None
        real = importlib.import_module(_real_name(name))
        snapshot = {a: getattr(real, a) for a in _IDENTITY_ATTRS if hasattr(real, a)}
        return importlib.util.spec_from_loader(name, _AliasLoader(real, snapshot))


def install(alias_name):
    """Bind ``alias_name`` to the real package and ensure the finder is active."""
    if not any(isinstance(f, _AliasFinder) for f in sys.meta_path):
        # Must precede the default PathFinder so alias submodule names map to the
        # real package instead of being re-executed as duplicate modules.
        sys.meta_path.insert(0, _AliasFinder())
    sys.modules[alias_name] = importlib.import_module(_REAL)

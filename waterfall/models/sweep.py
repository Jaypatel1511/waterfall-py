"""Excess-cash-flow (ECF) sweep mechanics.

Locked methodology: ECF is **derived from the ladder**, not an independent
formula — it is the cash remaining after Waterfall Priority steps 1-4:

    ECF = CFADS - senior fees (1) - senior debt service (2)
          - required reserve funding (3) - mezzanine debt service (4)

The mandatory sweep applies ``sweep% x ECF`` (per leverage band) to senior
prepayment; the retained ``(1 - sweep%) x ECF`` funds step-6 junior uses. A
cash-trap forces the sweep to **100%** so retained ECF is 0 and nothing reaches
steps 6-7 (no cash leaks to equity while the trap is active).
"""
from waterfall.data.schema import SweepConfig


def sweep_pct_for_leverage(config, leverage: float) -> float:
    """Sweep percentage for the current ``leverage`` from the banded config.

    Bands are stored ascending by ``max_leverage``; the tightest band that still
    covers the leverage (``leverage <= max_leverage``) applies. Above every band,
    ``default_sweep_pct`` applies. No config -> no mandatory sweep (0%).
    """
    if config is None:
        return 0.0
    for band in config.bands:
        if leverage <= band.max_leverage:
            return band.sweep_pct
    return config.default_sweep_pct


def apply_sweep(ecf_value: float, sweep_pct: float, cash_trap: bool = False):
    """Split ECF into (swept_to_senior_prepayment, retained_for_junior_uses).

    A negative ECF yields (0, 0) — there is no excess to sweep. Under a cash-trap
    the effective sweep is forced to 100%, so retained ECF is 0.
    """
    base = max(ecf_value, 0.0)
    pct = 1.0 if cash_trap else sweep_pct
    swept = base * pct
    retained = base - swept
    return swept, retained

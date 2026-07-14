"""Output data structures: per-period rows and the top-level DealResult.

Language guardrails (methodology, strictly enforced): the standard disclaimer
appears in three locations — report rendering, ``DealResult.limitations``, and
``DealResult.interpretation``. Every breach flag carries the mechanical-test-result
label (attached in the audit log).
"""
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional

STANDARD_DISCLAIMER = (
    "Mechanical waterfall computation only. Not a credit recommendation. "
    "CFADS inputs are user-supplied projections, not modeled cash flows."
)

LIMITATIONS = [
    "No NOI / CFADS projection modeling",
    "No construction-period modeling; the engine's clock starts at operations (period 0)",
    "Engine does not verify capex classification (maintenance vs. growth) or reserve "
    "classification (required vs. discretionary) — these are input-preparer responsibilities",
    "No tax modeling; no SPV tax-distribution (phantom-income) modeling",
    "No derivatives / hedge accounting",
    "No equity promote / carried interest (debt waterfall; equity is residual only)",
    "No CMBS bond-level tranching",
    "No A/B note structures or B-piece shortfall mechanics",
    "No preferred-equity / quasi-debt tranche",
    "No tax credit equity flips",
    "No defeasance (yield maintenance only)",
    "No OID modeling",
    "No sculpted-to-DSCR amortization (deferred — requires iterative solver)",
    "No ACT/ACT day-count (30/360, ACT/360, ACT/365F only)",
    "Single-currency only",
]

INTERPRETATION = (
    "Outputs are mechanical arithmetic over user-supplied CFADS and deal terms. "
    "Covenant-breach and default outputs are mechanical test results, never credit "
    "determinations; acceleration and remedies are contractual consequences the "
    "parties' documents assign, not determinations by this engine. " + STANDARD_DISCLAIMER
)


@dataclass
class PeriodResult:
    """One row of the period table (methodology Output Schema)."""
    period_index: int
    period_end_date: date
    cfads: float
    fees: float
    facility_draws: float
    equity_contributions: float
    debt_service_by_tranche: Dict[str, float]
    principal_by_tranche: Dict[str, float]
    interest_by_tranche: Dict[str, float]
    reserve_balances: Dict[str, float]
    reserve_draws: float
    reserve_releases: float
    proceeds_applied: float
    sweep_amount: float
    junior_uses: Dict[str, float]        # 6a growth capex / 6b top-ups / 6c distributions
    equity_distribution: float
    covenant_status: Dict[str, str]
    dscr: float


@dataclass
class DealResult:
    """Full engine output for a deal."""
    deal_name: str
    periods: List[PeriodResult] = field(default_factory=list)
    ledgers: List[object] = field(default_factory=list)         # List[PeriodLedger]
    audit_log: List[object] = field(default_factory=list)       # List[AuditRecord]
    tranche_summary: List[dict] = field(default_factory=list)
    covenant_status: List[dict] = field(default_factory=list)
    source_use: Dict[str, float] = field(default_factory=dict)  # close tie-out
    disclaimer: str = STANDARD_DISCLAIMER
    limitations: List[str] = field(default_factory=lambda: list(LIMITATIONS))
    interpretation: str = INTERPRETATION

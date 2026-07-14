"""Per-period ledger and audit log.

The ledger records **every** cash movement in a period, each tagged as a source
or a use, with a human-readable label. The period cash-conservation assertion
enumerates both sides from these entries (not a hardcoded list), so any modeled
mechanism is automatically covered.

The audit log records per-period decisions with rationale; breach entries carry
the mandated "mechanical test result" label.
"""
from dataclasses import dataclass, field
from typing import List

SOURCE = "source"
USE = "use"


@dataclass
class LedgerEntry:
    label: str
    amount: float
    kind: str   # SOURCE or USE


class PeriodLedger:
    """Ledger of cash sources and uses for a single period."""

    def __init__(self, period_index: int):
        self.period_index = period_index
        self.entries: List[LedgerEntry] = []

    def add_source(self, label: str, amount: float) -> None:
        self.entries.append(LedgerEntry(label, float(amount), SOURCE))

    def add_use(self, label: str, amount: float) -> None:
        self.entries.append(LedgerEntry(label, float(amount), USE))

    def total_sources(self) -> float:
        return sum(e.amount for e in self.entries if e.kind == SOURCE)

    def total_uses(self) -> float:
        return sum(e.amount for e in self.entries if e.kind == USE)

    def imbalance(self) -> float:
        return self.total_sources() - self.total_uses()


@dataclass
class AuditRecord:
    period_index: int
    event: str
    rationale: str
    mechanical_test_result: bool = False   # True on breach/default/cash-trap entries


MECHANICAL_TEST_LABEL = (
    "mechanical test result computed by the engine from user-supplied CFADS and "
    "the deal terms"
)


class AuditLog:
    """Ordered per-period decision log."""

    def __init__(self):
        self.records: List[AuditRecord] = []

    def record(self, period_index: int, event: str, rationale: str,
               mechanical_test_result: bool = False) -> None:
        self.records.append(
            AuditRecord(period_index, event, rationale, mechanical_test_result)
        )

    def breaches(self) -> List[AuditRecord]:
        return [r for r in self.records if r.mechanical_test_result]

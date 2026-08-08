from __future__ import annotations

from dataclasses import dataclass
from enum import Enum


class Severity(str, Enum):
    ERROR = "error"  # FAIL — blocks creation/load/render
    WARN = "warn"  # banner only


@dataclass(frozen=True)
class ContractIssue:
    severity: Severity
    code: str
    message: str

    def snapshot_dict(self) -> dict:
        return {"severity": self.severity.value, "code": self.code, "message": self.message}

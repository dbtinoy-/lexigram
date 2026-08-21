"""Shared types for the Lexigram architectural rule catalog."""

from __future__ import annotations

import ast
from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum
from pathlib import Path


class RuleSeverity(str, Enum):
    """Severity level for a Lexigram architectural rule finding."""

    CRITICAL = "critical"
    IMPORTANT = "important"
    MINOR = "minor"


SEVERITY_ORDER = {
    RuleSeverity.CRITICAL: 0,
    RuleSeverity.IMPORTANT: 1,
    RuleSeverity.MINOR: 2,
}

ALLOWED_CROSS_EXTENSION_IMPORTS: dict[str, frozenset[str]] = {
    "lexigram-admin": frozenset(
        {
            "lexigram-auth",
            "lexigram-cache",
            "lexigram-features",
            "lexigram-resilience",
            "lexigram-ui",
        }
    ),
    "lexigram-web": frozenset({"lexigram-ui"}),
    "lexigram-events": frozenset({"lexigram-resilience"}),
    "lexigram-tasks": frozenset({"lexigram-resilience"}),
    "lexigram-monitor": frozenset({"lexigram-tasks"}),
    "lexigram-multimedia": frozenset(
        {
            "lexigram-multimedia-beat",
            "lexigram-multimedia-image",
            "lexigram-multimedia-interpolate",
            "lexigram-multimedia-music",
            "lexigram-multimedia-tts",
            "lexigram-multimedia-upscale",
            "lexigram-multimedia-video",
            "lexigram-tasks",
        }
    ),
    "lexigram-ai-governance": frozenset({"lexigram-tasks"}),
    "lexigram-ai": frozenset(
        {
            "lexigram-vector",
            "lexigram-ai-agents",
            "lexigram-ai-feedback",
            "lexigram-ai-governance",
            "lexigram-ai-guard",
            "lexigram-ai-llm",
            "lexigram-ai-mcp",
            "lexigram-ai-memory",
            "lexigram-ai-observability",
            "lexigram-ai-prompt",
            "lexigram-ai-rag",
            "lexigram-ai-session",
            "lexigram-ai-skills",
            "lexigram-ai-workers",
        }
    ),
}


@dataclass(frozen=True, slots=True)
class RuleFinding:
    """Single rule violation captured from static Lexigram analysis."""

    rule_id: str
    severity: RuleSeverity
    owner: str
    rationale: str
    package_name: str
    path: Path
    line: int
    message: str


@dataclass(frozen=True, slots=True)
class RuleSourceFile:
    """Python source file prepared for rule evaluation."""

    package_name: str
    package_root: Path
    path: Path
    relative_path: Path
    module_name: str
    tree: ast.Module


@dataclass(frozen=True, slots=True)
class RuleCatalogContext:
    """Shared lookup context available to every rule detector."""

    root: Path
    module_owners: Mapping[str, frozenset[str]]

    def resolve_import_owner(self, module_name: str) -> str | None:
        """Resolve the owning package for a Python import path."""

        best_match: tuple[str, frozenset[str]] | None = None
        for prefix, owners in self.module_owners.items():
            if module_name != prefix and not module_name.startswith(f"{prefix}."):
                continue
            if best_match is None or len(prefix) > len(best_match[0]):
                best_match = (prefix, owners)
        if best_match is None:
            return None
        if len(best_match[1]) != 1:
            return None
        return next(iter(best_match[1]))


@dataclass(frozen=True, slots=True)
class RuleDefinition:
    """Metadata and detector callback for one Lexigram rule."""

    rule_id: str
    severity: RuleSeverity
    owner: str
    rationale: str
    detector: Callable[[RuleSourceFile, RuleCatalogContext], tuple[RuleFinding, ...]]


def _finding(
    source_file: RuleSourceFile,
    *,
    rule_id: str,
    severity: RuleSeverity,
    owner: str,
    rationale: str,
    line: int,
    message: str,
) -> RuleFinding:
    """Create a normalized rule finding for one source location."""

    return RuleFinding(
        rule_id=rule_id,
        severity=severity,
        owner=owner,
        rationale=rationale,
        package_name=source_file.package_name,
        path=source_file.relative_path,
        line=line,
        message=message,
    )


def make_rule_finding(
    *,
    rule_id: str,
    severity: RuleSeverity,
    owner: str,
    rationale: str,
    package_name: str,
    path: Path,
    line: int,
    message: str,
) -> RuleFinding:
    """Build a rule finding outside the AST-backed detector flow."""

    return RuleFinding(
        rule_id=rule_id,
        severity=severity,
        owner=owner,
        rationale=rationale,
        package_name=package_name,
        path=path,
        line=line,
        message=message,
    )

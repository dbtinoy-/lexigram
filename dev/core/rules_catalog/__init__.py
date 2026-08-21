"""Lexigram architectural rule catalog.

Public API: :func:`build_rules_catalog` plus the finding/definition
types consumed by the rule engine and audit generators. Detectors are
split by family across :mod:`structure_rules` and :mod:`security_rules`,
wired together in :mod:`catalog`.
"""

from __future__ import annotations

from dev.core.rules_catalog.catalog import build_rules_catalog
from dev.core.rules_catalog.types import (
    ALLOWED_CROSS_EXTENSION_IMPORTS,
    SEVERITY_ORDER,
    make_rule_finding,
    RuleCatalogContext,
    RuleDefinition,
    RuleFinding,
    RuleSeverity,
    RuleSourceFile,
)

__all__ = [
    "ALLOWED_CROSS_EXTENSION_IMPORTS",
    "SEVERITY_ORDER",
    "RuleCatalogContext",
    "RuleDefinition",
    "RuleFinding",
    "RuleSeverity",
    "RuleSourceFile",
    "build_rules_catalog",
    "make_rule_finding",
]

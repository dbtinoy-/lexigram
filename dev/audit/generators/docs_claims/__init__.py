"""Docs claims audit generator package.

Public API: :class:`DocsClaimsAuditGenerator` plus the introspection
and registry helpers consumed by the docs-defaults audit
(:mod:`introspect`, :mod:`registry`, :mod:`claims`).
"""

from __future__ import annotations

from dev.audit.generators.docs_claims.generator import DocsClaimsAuditGenerator
from dev.audit.generators.docs_claims.introspect import (
    _driver_segment,
    _field_names,
    _is_config_class,
    _mapping_value,
    _sequence_element,
    _union_members,
)
from dev.audit.generators.docs_claims.registry import (
    _build_direct_reads,
    _build_env_validity,
    _try_import,
)
from dev.audit.generators.docs_claims.claims import _verify_env_var

__all__ = [
    "DocsClaimsAuditGenerator",
    "_build_direct_reads",
    "_build_env_validity",
    "_driver_segment",
    "_field_names",
    "_is_config_class",
    "_mapping_value",
    "_sequence_element",
    "_try_import",
    "_union_members",
    "_verify_env_var",
]

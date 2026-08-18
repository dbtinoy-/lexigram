from __future__ import annotations

from dev.audit.generators.base import AuditGeneratorProtocol, AuditRunResult
from dev.audit.generators.dependencies import DependenciesAuditGenerator
from dev.audit.generators.docs_claims import DocsClaimsAuditGenerator
from dev.audit.generators.docs_imports import DocsImportsAuditGenerator
from dev.audit.generators.docs_links import DocsLinksAuditGenerator
from dev.audit.generators.env_vars import EnvVarsAuditGenerator
from dev.audit.generators.index import AuditIndexGenerator
from dev.audit.generators.integrations import IntegrationsAuditGenerator
from dev.audit.generators.optional_imports import OptionalImportsAuditGenerator
from dev.audit.generators.overview import OverviewAuditGenerator
from dev.audit.generators.protocols import ProtocolsAuditGenerator
from dev.audit.generators.quality import QualityAuditGenerator
from dev.audit.generators.registry import build_audit_registry
from dev.audit.generators.security import SecurityAuditGenerator
from dev.audit.generators.tests import TestsAuditGenerator

__all__ = [
    "AuditGeneratorProtocol",
    "AuditIndexGenerator",
    "AuditRunResult",
    "DependenciesAuditGenerator",
    "DocsClaimsAuditGenerator",
    "DocsImportsAuditGenerator",
    "DocsLinksAuditGenerator",
    "EnvVarsAuditGenerator",
    "IntegrationsAuditGenerator",
    "OptionalImportsAuditGenerator",
    "OverviewAuditGenerator",
    "ProtocolsAuditGenerator",
    "QualityAuditGenerator",
    "SecurityAuditGenerator",
    "TestsAuditGenerator",
    "build_audit_registry",
]

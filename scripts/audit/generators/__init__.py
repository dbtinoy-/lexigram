from __future__ import annotations

from scripts.audit.generators.base import AuditGeneratorProtocol, AuditRunResult
from scripts.audit.generators.docs_claims import DocsClaimsAuditGenerator
from scripts.audit.generators.docs_imports import DocsImportsAuditGenerator
from scripts.audit.generators.docs_links import DocsLinksAuditGenerator
from scripts.audit.generators.env_vars import EnvVarsAuditGenerator
from scripts.audit.generators.index import AuditIndexGenerator
from scripts.audit.generators.integrations import IntegrationsAuditGenerator
from scripts.audit.generators.optional_imports import OptionalImportsAuditGenerator
from scripts.audit.generators.overview import OverviewAuditGenerator
from scripts.audit.generators.protocols import ProtocolsAuditGenerator
from scripts.audit.generators.quality import QualityAuditGenerator
from scripts.audit.generators.registry import build_audit_registry
from scripts.audit.generators.security import SecurityAuditGenerator
from scripts.audit.generators.tests import TestsAuditGenerator

__all__ = [
    "AuditGeneratorProtocol",
    "AuditIndexGenerator",
    "AuditRunResult",
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

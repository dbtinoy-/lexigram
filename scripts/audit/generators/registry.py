from __future__ import annotations

from scripts.audit.generators.base import AuditGeneratorProtocol
from scripts.audit.generators.dependencies import DependenciesAuditGenerator
from scripts.audit.generators.docs_claims import DocsClaimsAuditGenerator
from scripts.audit.generators.docs_defaults import DocsDefaultsAuditGenerator
from scripts.audit.generators.docs_imports import DocsImportsAuditGenerator
from scripts.audit.generators.docs_links import DocsLinksAuditGenerator
from scripts.audit.generators.env_vars import EnvVarsAuditGenerator
from scripts.audit.generators.index import AuditIndexGenerator
from scripts.audit.generators.integrations import IntegrationsAuditGenerator
from scripts.audit.generators.optional_imports import OptionalImportsAuditGenerator
from scripts.audit.generators.overview import OverviewAuditGenerator
from scripts.audit.generators.protocols import ProtocolsAuditGenerator
from scripts.audit.generators.quality import QualityAuditGenerator
from scripts.audit.generators.rules import RulesAuditGenerator
from scripts.audit.generators.security import SecurityAuditGenerator
from scripts.audit.generators.tests import TestsAuditGenerator
from scripts.core.registry import GeneratorRegistry


def build_audit_registry() -> GeneratorRegistry[AuditGeneratorProtocol]:
    """Build a registry populated with all supported audit generators."""

    registry = GeneratorRegistry[AuditGeneratorProtocol]()
    for generator in (
        DependenciesAuditGenerator(),
        DocsClaimsAuditGenerator(),
        DocsDefaultsAuditGenerator(),
        DocsImportsAuditGenerator(),
        DocsLinksAuditGenerator(),
        EnvVarsAuditGenerator(),
        IntegrationsAuditGenerator(),
        OverviewAuditGenerator(),
        ProtocolsAuditGenerator(),
        OptionalImportsAuditGenerator(),
        QualityAuditGenerator(),
        RulesAuditGenerator(),
        SecurityAuditGenerator(),
        TestsAuditGenerator(),
        AuditIndexGenerator(),
    ):
        registry.register(generator.name, generator)
    return registry

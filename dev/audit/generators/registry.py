from __future__ import annotations

from dev.audit.generators.base import AuditGeneratorProtocol
from dev.audit.generators.dependencies import DependenciesAuditGenerator
from dev.audit.generators.docs_claims import DocsClaimsAuditGenerator
from dev.audit.generators.docs_defaults import DocsDefaultsAuditGenerator
from dev.audit.generators.docs_imports import DocsImportsAuditGenerator
from dev.audit.generators.docs_links import DocsLinksAuditGenerator
from dev.audit.generators.env_vars import EnvVarsAuditGenerator
from dev.audit.generators.index import AuditIndexGenerator
from dev.audit.generators.integrations import IntegrationsAuditGenerator
from dev.audit.generators.optional_imports import OptionalImportsAuditGenerator
from dev.audit.generators.overview import OverviewAuditGenerator
from dev.audit.generators.protocols import ProtocolsAuditGenerator
from dev.audit.generators.quality import QualityAuditGenerator
from dev.audit.generators.rules import RulesAuditGenerator
from dev.audit.generators.security import SecurityAuditGenerator
from dev.audit.generators.tests import TestsAuditGenerator
from dev._lib.registry import GeneratorRegistry


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

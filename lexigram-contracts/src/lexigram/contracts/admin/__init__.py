"""Admin contracts — protocols and types for the admin contributor system."""

from __future__ import annotations

from lexigram.contracts.admin.action_hooks import ActionHookProtocol, HasActionHooks
from lexigram.contracts.admin.audit_entry import AuditEntry, AuditOutcome
from lexigram.contracts.admin.audit_logger import AdminAuditLoggerProtocol
from lexigram.contracts.admin.cache_provider import CacheProviderProtocol
from lexigram.contracts.admin.contributor import BaseAdminContributor
from lexigram.contracts.admin.cqrs import AdminCommand, AdminQuery
from lexigram.contracts.admin.errors import (
    AdminError,
    HealthCheckNotFoundError,
    WidgetNotFoundError,
)
from lexigram.contracts.admin.health_payload import HealthCheckPayload
from lexigram.contracts.admin.operations import (
    AdminSearchableProtocol,
    AggregatableProtocol,
    AuditableProtocol,
    BulkOperationsProtocol,
    CacheAwareProtocol,
    ExportableProtocol,
    RelationLoaderProtocol,
    TransactionalProtocol,
    ValidatableProtocol,
)
from lexigram.contracts.admin.page_handler import (
    AdminPageHandlerProtocol,
    ManagementPageHandler,
)
from lexigram.contracts.admin.pii_redactor import PiiRedactorProtocol
from lexigram.contracts.admin.protocols import (
    AdminContributorProtocol,
    AdminContributorRegistryProtocol,
    AdminDashboardProtocol,
)
from lexigram.contracts.admin.repository import AdminRepositoryProtocol
from lexigram.contracts.admin.route_spec import AdminRouteSpec
from lexigram.contracts.admin.types import (
    AdminActionDefinition,
    AdminHealthDefinition,
    DashboardWidgetDefinition,
    ManagementPageDefinition,
    NavigationContribution,
    PageCategory,
    PageFilterField,
    SettingsPanelDefinition,
    WidgetCategory,
    WidgetParams,
    WidgetSize,
    WidgetViewModel,
)
from lexigram.contracts.admin.widget_content import (
    ChartContent,
    ChartPoint,
    EmptyContent,
    MessageContent,
    Stat,
    StatContent,
    TableCell,
    TableContent,
    Tone,
    WidgetContent,
    WidgetKind,
)
from lexigram.contracts.admin.widget_protocols import (
    WidgetHandlerProtocol,
    WidgetRendererProtocol,
)
from lexigram.contracts.data.data_source import DataSourceProtocol

__all__ = [
    "ActionHookProtocol",
    "AdminActionDefinition",
    "AdminAuditLoggerProtocol",
    "AdminCommand",
    "AdminContributorProtocol",
    "AdminContributorRegistryProtocol",
    "AdminDashboardProtocol",
    "AdminError",
    "AdminHealthDefinition",
    "AdminPageHandlerProtocol",
    "AdminQuery",
    "AdminRepositoryProtocol",
    "AdminRouteSpec",
    "AdminSearchableProtocol",
    "AggregatableProtocol",
    "AuditEntry",
    "AuditOutcome",
    "AuditableProtocol",
    "BaseAdminContributor",
    "BulkOperationsProtocol",
    "CacheAwareProtocol",
    "CacheProviderProtocol",
    "ChartContent",
    "ChartPoint",
    "DashboardWidgetDefinition",
    "DataSourceProtocol",
    "EmptyContent",
    "ExportableProtocol",
    "HasActionHooks",
    "HealthCheckNotFoundError",
    "HealthCheckPayload",
    "ManagementPageDefinition",
    "ManagementPageHandler",
    "MessageContent",
    "NavigationContribution",
    "PageCategory",
    "PageFilterField",
    "PiiRedactorProtocol",
    "RelationLoaderProtocol",
    "SettingsPanelDefinition",
    "Stat",
    "StatContent",
    "TableCell",
    "TableContent",
    "Tone",
    "TransactionalProtocol",
    "ValidatableProtocol",
    "WidgetCategory",
    "WidgetContent",
    "WidgetHandlerProtocol",
    "WidgetKind",
    "WidgetNotFoundError",
    "WidgetParams",
    "WidgetRendererProtocol",
    "WidgetSize",
    "WidgetViewModel",
]

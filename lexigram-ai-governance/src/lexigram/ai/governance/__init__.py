"""AI Governance sub-package."""

from __future__ import annotations

from importlib.metadata import PackageNotFoundError, version
from typing import TYPE_CHECKING, Any

try:
    __version__ = version("lexigram-ai-governance")
except PackageNotFoundError:
    __version__ = "0.0.0"

if TYPE_CHECKING:
    from lexigram.ai.governance.audit import (
        AIAuditEvent,
        AIAuditStore,
        AuditEventType,
        AuditQuery,
        AuditSummary,
        InMemoryAuditStore,
    )
    from lexigram.ai.governance.config import GovernanceConfig
    from lexigram.ai.governance.content_gate import (
        AlwaysAllowGate,
        CompositeGate,
        ContentPolicyGateProtocol,
        ContentPolicyService,
        PolicyDecision,
        PolicyObserverProtocol,
        PolicyOutcome,
        PolicyRequest,
    )
    from lexigram.ai.governance.di.provider import GovernanceProvider
    from lexigram.ai.governance.exceptions import (
        BudgetExceededError,
        GovernanceError,
        ModelAccessDeniedError,
        RateLimitExceededError,
        ResourceExhaustedError,
    )
    from lexigram.ai.governance.hooks import (
        GovernanceAuditRecordedHook,
        GovernancePersistenceWrittenHook,
        GovernancePolicyEvaluatedHook,
    )
    from lexigram.ai.governance.module import GovernanceModule
    from lexigram.ai.governance.persistence import (
        GovernancePersistence,
        InMemoryGovernancePersistence,
        RedisGovernancePersistence,
    )
    from lexigram.ai.governance.resource.reconciliation import (
        GaugeReconciliationCallback,
        GaugeReconciliationWorker,
    )
    from lexigram.ai.governance.resource.registry import (
        ResourceUnitRegistry,
    )
    from lexigram.ai.governance.resource.tracker import (
        ResourceUnitTracker,
    )
    from lexigram.ai.governance.services.manager import AIGovernanceManager

_LAZY_IMPORTS: dict[str, tuple[str, str]] = {
    # --- Content Gate ---
    "AlwaysAllowGate": (
        "lexigram.ai.governance.content_gate",
        "AlwaysAllowGate",
    ),
    "CompositeGate": (
        "lexigram.ai.governance.content_gate",
        "CompositeGate",
    ),
    "ContentPolicyGateProtocol": (
        "lexigram.ai.governance.content_gate",
        "ContentPolicyGateProtocol",
    ),
    "ContentPolicyService": (
        "lexigram.ai.governance.content_gate",
        "ContentPolicyService",
    ),
    "PolicyDecision": (
        "lexigram.ai.governance.content_gate",
        "PolicyDecision",
    ),
    "PolicyObserverProtocol": (
        "lexigram.ai.governance.content_gate",
        "PolicyObserverProtocol",
    ),
    "PolicyOutcome": (
        "lexigram.ai.governance.content_gate",
        "PolicyOutcome",
    ),
    "PolicyRequest": (
        "lexigram.ai.governance.content_gate",
        "PolicyRequest",
    ),
    # --- Audit ---
    "AIAuditEvent": ("lexigram.ai.governance.audit", "AIAuditEvent"),
    "AIAuditStore": ("lexigram.ai.governance.audit", "AIAuditStore"),
    "AuditEventType": ("lexigram.ai.governance.audit", "AuditEventType"),
    "AuditQuery": ("lexigram.ai.governance.audit", "AuditQuery"),
    "AuditSummary": ("lexigram.ai.governance.audit", "AuditSummary"),
    "InMemoryAuditStore": ("lexigram.ai.governance.audit", "InMemoryAuditStore"),
    # --- Config ---
    "GovernanceConfig": ("lexigram.ai.governance.config", "GovernanceConfig"),
    # --- DI ---
    "GovernanceProvider": ("lexigram.ai.governance.di.provider", "GovernanceProvider"),
    "GovernanceModule": ("lexigram.ai.governance.module", "GovernanceModule"),
    # --- Exceptions ---
    "GovernanceError": ("lexigram.ai.governance.exceptions", "GovernanceError"),
    "BudgetExceededError": ("lexigram.ai.governance.exceptions", "BudgetExceededError"),
    "ModelAccessDeniedError": (
        "lexigram.ai.governance.exceptions",
        "ModelAccessDeniedError",
    ),
    "RateLimitExceededError": (
        "lexigram.ai.governance.exceptions",
        "RateLimitExceededError",
    ),
    # --- Hooks ---
    "GovernanceAuditRecordedHook": (
        "lexigram.ai.governance.hooks",
        "GovernanceAuditRecordedHook",
    ),
    "GovernancePersistenceWrittenHook": (
        "lexigram.ai.governance.hooks",
        "GovernancePersistenceWrittenHook",
    ),
    "GovernancePolicyEvaluatedHook": (
        "lexigram.ai.governance.hooks",
        "GovernancePolicyEvaluatedHook",
    ),
    # --- Persistence ---
    "GovernancePersistence": (
        "lexigram.ai.governance.persistence",
        "GovernancePersistence",
    ),
    "InMemoryGovernancePersistence": (
        "lexigram.ai.governance.persistence",
        "InMemoryGovernancePersistence",
    ),
    "RedisGovernancePersistence": (
        "lexigram.ai.governance.persistence",
        "RedisGovernancePersistence",
    ),
    # --- Resource ---
    "ResourceExhaustedError": (
        "lexigram.ai.governance.exceptions",
        "ResourceExhaustedError",
    ),
    "ResourceUnitRegistry": (
        "lexigram.ai.governance.resource.registry",
        "ResourceUnitRegistry",
    ),
    "ResourceUnitTracker": (
        "lexigram.ai.governance.resource.tracker",
        "ResourceUnitTracker",
    ),
    "GaugeReconciliationCallback": (
        "lexigram.ai.governance.resource.reconciliation",
        "GaugeReconciliationCallback",
    ),
    "GaugeReconciliationWorker": (
        "lexigram.ai.governance.resource.reconciliation",
        "GaugeReconciliationWorker",
    ),
    # --- Services ---
    "AIGovernanceManager": (
        "lexigram.ai.governance.services.manager",
        "AIGovernanceManager",
    ),
    # --- Protocols ---
    "AIAuditStoreProtocol": (
        "lexigram.ai.governance.protocols",
        "AIAuditStoreProtocol",
    ),
    "AIGovernanceProtocol": (
        "lexigram.ai.governance.protocols",
        "AIGovernanceProtocol",
    ),
    "CostTrackingProtocol": (
        "lexigram.ai.governance.protocols",
        "CostTrackingProtocol",
    ),
    # --- Events ---
    "PolicyEvaluatedEvent": ("lexigram.ai.governance.events", "PolicyEvaluatedEvent"),
}


def __getattr__(name: str) -> Any:
    """Lazy-load symbols on first access."""
    if name in _LAZY_IMPORTS:
        import importlib

        module_path, attr_name = _LAZY_IMPORTS[name]
        module = importlib.import_module(module_path)
        value = getattr(module, attr_name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    """Enumerate available attributes for IDE support."""
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = [
    "AIAuditEvent",
    "AIAuditStore",
    "AIAuditStoreProtocol",
    "AIGovernanceManager",
    "AIGovernanceProtocol",
    "AlwaysAllowGate",
    "AuditEventType",
    "AuditQuery",
    "AuditSummary",
    "BudgetExceededError",
    "CompositeGate",
    "ContentPolicyGateProtocol",
    "ContentPolicyService",
    "CostTrackingProtocol",
    "GaugeReconciliationCallback",
    "GaugeReconciliationWorker",
    "GovernanceAuditRecordedHook",
    "GovernanceConfig",
    "GovernanceError",
    "GovernanceModule",
    "GovernancePersistence",
    "GovernancePersistenceWrittenHook",
    "GovernancePolicyEvaluatedHook",
    "GovernanceProvider",
    "InMemoryAuditStore",
    "InMemoryGovernancePersistence",
    "ModelAccessDeniedError",
    "PolicyDecision",
    "PolicyEvaluatedEvent",
    "PolicyObserverProtocol",
    "PolicyOutcome",
    "PolicyRequest",
    "RateLimitExceededError",
    "RedisGovernancePersistence",
    "ResourceExhaustedError",
    "ResourceUnitRegistry",
    "ResourceUnitTracker",
]

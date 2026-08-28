"""Application service that presents Lexigram's flag manager as a release desk."""

from __future__ import annotations

from dataclasses import asdict
from datetime import UTC, datetime
from typing import Any

from lexigram.features.backends.local import LocalProvider
from lexigram.features.config import FeatureFlagsConfig
from lexigram.features.manager import FlagManager
from lexigram.features.types import Flag, FlagContext, FlagType
from release_control.config import ReleaseControlConfig


class ReleaseControlService:
    """Own the demo scenario while delegating flag behavior to Lexigram.

    The lab intentionally keeps the application state in the package-owned
    ``FlagManager``: overrides, evaluation caching, variants, and the audit
    trail are all real Lexigram behavior rather than look-alike demo classes.
    """

    _FLAG_NAMES = ("new_checkout", "search_experiment", "ai_assistant")

    def __init__(
        self,
        manager: FlagManager,
        config: ReleaseControlConfig,
        feature_config: FeatureFlagsConfig,
    ) -> None:
        self._manager = manager
        self._config = config
        self._feature_config = feature_config

        definitions = {
            "new_checkout": Flag(
                name="new_checkout",
                type=FlagType.PERCENTAGE,
                enabled=True,
                percentage=50,
                description="Gradual rollout for the new checkout experience",
            ),
            "search_experiment": Flag(
                name="search_experiment",
                type=FlagType.VARIANT,
                enabled=True,
                variants={"control": 50, "ranked": 50},
                default_variant="control",
                description="Deterministic A/B search ranking experiment",
            ),
            "ai_assistant": Flag(
                name="ai_assistant",
                type=FlagType.USER_ATTRIBUTE,
                enabled=True,
                user_attributes={"plan": "pro"},
                description="Available only to users on the pro plan",
            ),
        }

        # The package provider seeds the simple YAML flags. We add richer
        # definitions through the public manager API so this demo can expose
        # percentage, variant, and attribute evaluation in one screen.
        for name, enabled in self._feature_config.initial_flags.items():
            if name in definitions:
                definitions[name].enabled = enabled
        self._manager.add_provider(LocalProvider(definitions))

    @staticmethod
    def _context(user_id: str, plan: str) -> FlagContext:
        return FlagContext(
            user_id=user_id.strip() or "demo-user-42",
            user_attributes={"plan": plan.strip().lower() or "free"},
        )

    async def snapshot(
        self, user_id: str = "demo-user-42", plan: str = "pro"
    ) -> dict[str, Any]:
        """Evaluate every flag for the supplied deterministic user context."""
        context = self._context(user_id, plan)
        flags: list[dict[str, Any]] = []
        for name in self._FLAG_NAMES:
            evaluation = await self._manager.evaluate(name, context)
            effective = await self._manager.is_enabled(name, context)
            variant = await self._manager.get_variant(name, context, default="")
            flags.append(
                {
                    "name": name,
                    "enabled": effective,
                    "base_enabled": evaluation.enabled,
                    "value": evaluation.value,
                    "variant": variant or None,
                    "reason": evaluation.reason,
                    "override": self._manager.get_override_state(name),
                    "description": self._description(name),
                }
            )
        return {
            "context": {
                "user_id": context.user_id,
                "plan": plan.strip().lower() or "free",
            },
            "flags": flags,
            "cache_ttl_seconds": self._cache_ttl(),
            "audit_count": len(self._manager.get_audit_log()),
        }

    async def evaluate(self, name: str, user_id: str, plan: str) -> dict[str, Any]:
        """Evaluate one flag with an explicit context for the UI."""
        if name not in self._FLAG_NAMES:
            raise ValueError(f"Unknown flag: {name}")
        context = self._context(user_id, plan)
        evaluation = await self._manager.evaluate(name, context)
        return {
            "name": name,
            "enabled": await self._manager.is_enabled(name, context),
            "base_enabled": evaluation.enabled,
            "value": evaluation.value,
            "variant": await self._manager.get_variant(name, context, default="")
            or None,
            "reason": evaluation.reason,
            "context": {"user_id": context.user_id, "plan": plan},
            "override": self._manager.get_override_state(name),
        }

    def set_override(self, name: str, enabled: bool, actor: str | None = None) -> None:
        """Force one flag on or off using the package audit-aware API."""
        if name not in self._FLAG_NAMES:
            raise ValueError(f"Unknown flag: {name}")
        resolved_actor = (
            actor or self._config.default_actor
        ).strip() or self._config.default_actor
        # Call the concrete manager methods so the actor is retained for both
        # directions; the package convenience method currently forwards the
        # disable branch without its optional actor.
        if enabled:
            self._manager.enable(name, actor=resolved_actor)
        else:
            self._manager.disable(name, actor=resolved_actor)

    def clear_override(self, name: str) -> None:
        """Return a flag to its configured provider behavior."""
        if name not in self._FLAG_NAMES:
            raise ValueError(f"Unknown flag: {name}")
        self._manager.clear_override(name)

    async def clear_cache(self) -> None:
        """Expose TTL cache invalidation as an intentional lab action."""
        await self._manager.clear_cache()

    def audit(self) -> list[dict[str, Any]]:
        """Serialize the package-owned override audit entries for the browser."""
        entries: list[dict[str, Any]] = []
        for entry in self._manager.get_audit_log():
            item = asdict(entry)
            timestamp = item.get("timestamp")
            if isinstance(timestamp, datetime):
                item["timestamp"] = timestamp.astimezone(UTC).isoformat()
            entries.append(item)
        return list(reversed(entries))

    def _description(self, name: str) -> str:
        return {
            "new_checkout": "50% percentage rollout",
            "search_experiment": "50/50 deterministic variants",
            "ai_assistant": "user attribute: plan = pro",
        }[name]

    def _cache_ttl(self) -> int:
        return self._feature_config.cache_ttl


__all__ = ["ReleaseControlService"]

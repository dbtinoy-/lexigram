from __future__ import annotations

from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from lexigram import serialization as json
from lexigram.admin.models.setting import SystemSetting
from lexigram.admin.settings.panel.utils import map_config_node_type
from lexigram.contracts.infra.cache import CacheBackendProtocol
from lexigram.domain import DomainModel
from lexigram.logging import get_logger

logger = get_logger(__name__)
_registry_warned = [False]


def _warn_registry_unavailable() -> None:
    """Emit a one-off warning when the admin panel registry is unavailable."""

    if _registry_warned[0]:
        return
    _registry_warned[0] = True
    logger.warning(
        "config_registry_unavailable",
        hint="pip install lexigram-admin",
        detail="falling back to legacy settings resolution",
    )


@runtime_checkable
class _SettingsRepository(Protocol):
    """Narrow structural protocol for the settings storage backend.

    Avoids a direct import of ``GenericRepository`` from ``lexigram-sql``.
    """

    async def find_one(self, **filters: Any) -> Any: ...

    async def update(self, entity: Any) -> Any: ...

    async def create(self, data: Any) -> Any: ...


# Events integration
from lexigram.contracts.domain import DomainEvent
from lexigram.di.decorators import inject

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol


class SettingUpdated(DomainEvent):
    """Fired when a setting is changed."""

    key: str
    value: str
    scope: str
    scope_id: str


@dataclass(init=False)
class SettingDefinition(DomainModel):
    """Defines a comprehensive schema for a configuration setting."""

    key: str
    scope: list[str] = field(
        default_factory=lambda: ["global"]
    )  # ["global", "tenant", "user"]
    type: str = "string"  # string, int, bool, json, secret, enum
    default: Any = None
    options: list[str] | dict[str, str] | None = None  # For enums
    label: str = ""
    description: str | None = None
    category: str = "General"
    is_public: bool = False
    validation_rules: str | None = None  # e.g. "min:1|max:100"


class SettingsRegistry:
    """Registry for setting definitions."""

    _definitions: dict[str, SettingDefinition] = {}

    @classmethod
    def register(cls, definition: SettingDefinition) -> Any:
        cls._definitions[definition.key] = definition

    @classmethod
    def get(cls, key: str) -> SettingDefinition | None:
        return cls._definitions.get(key)

    @classmethod
    def get_all(cls) -> list[SettingDefinition]:
        return list(cls._definitions.values())

    @classmethod
    def get_for_scope(cls, scope: str) -> list[SettingDefinition]:
        return list(filter(lambda d: scope in d.scope, cls._definitions.values()))


@inject
class SettingsService:
    """Service for managing implementation and resolution of settings."""

    def __init__(
        self,
        repository: _SettingsRepository,
        event_bus: Any = None,
        cache: CacheBackendProtocol | None = None,
    ):
        self.repo = repository
        self.registry = SettingsRegistry()
        self.event_bus = event_bus
        self.cache = cache

    async def get(self, key: str, context: Any | None = None) -> Any:
        """
        Resolve a setting value with cascading logic and caching.
        """
        definition = self.registry.get(key)

        # 1. Try Cache if available
        cache_key = self._get_cache_key(key, context)
        if self.cache:
            try:
                res = await self.cache.get(cache_key)
                if res.is_ok():
                    cached = res.unwrap()
                    if cached is not None:
                        return cached
            except (RuntimeError, ValueError, OSError) as e:
                logger.warning("Cache lookup failed for %s: %s", key, e)

        # 2. Cascading Strategy:
        resolved_val = await self._resolve_cascaded(key, context, definition)

        # 3. Cache and return
        if self.cache:
            try:
                await self.cache.set(cache_key, resolved_val, ttl=3600)
            except (RuntimeError, ValueError, OSError):
                logger.exception("Cache set failed")

        return resolved_val

    async def _resolve_cascaded(
        self,
        key: str,
        context: Any | None,
        definition: SettingDefinition | None,
    ) -> Any:
        # 1. Env Override (Highest Priority) - LEX_KEY_STYLE
        env_val = self._get_from_env(key)
        if env_val is not None:
            return self._cast_value(env_val, definition)

        # 2. Database: User Scope
        if context:
            user = getattr(context, "user", None) or getattr(
                getattr(context, "state", None),
                "user",
                None,
            )
            # Prefer canonical `user_id` attribute on user objects
            if user and hasattr(user, "user_id"):
                user_val = await self._get_from_repo(key, "user", str(user.user_id))
                if user_val is not None:
                    return self._cast_value(user_val, definition)

        # 3. Database: Global Scope
        global_val = await self._get_from_repo(key, "global", "system")
        if global_val is not None:
            return self._cast_value(global_val, definition)

        # 4. YAML Config (LexigramConfig)
        yaml_val = self._get_from_yaml_config(key)
        if yaml_val is not None:
            return yaml_val

        # 5. Default from Registry Definition
        if definition:
            return definition.default

        # 6. Fallback to ConfigRegistry for new ConfigSpecs
        try:
            from lexigram.admin.lib.di import get_admin_resolver
            from lexigram.admin.settings.panel.registry import ConfigRegistry

            resolver = get_admin_resolver(context)
            registry = await resolver.resolve(ConfigRegistry)
            node = registry.get_node(key)
            if node:
                return node.default
        except ImportError:
            _warn_registry_unavailable()

        return None

    def _get_from_env(self, key: str) -> str | None:
        """Get value from environment variable (LEX_ADMIN__KEY__STYLE)."""
        import os

        env_key = f"LEX_ADMIN__{key.upper().replace('.', '__')}"
        return os.environ.get(env_key)

    def _get_from_yaml_config(self, key: str) -> Any:
        """Get value from boot-time config via LexigramConfig.

        Traverses the boot config dict using dot-separated keys.
        """
        try:
            from lexigram.config import LexigramConfig

            config = LexigramConfig.boot_config()  # type: ignore[attr-defined]
            config_dict = config.model_dump()
            parts = key.split(".")
            curr = config_dict
            for p in parts:
                if isinstance(curr, dict) and p in curr:
                    curr = curr[p]
                else:
                    return None
            return curr
        except (ImportError, RuntimeError):
            return None

    def _get_cache_key(self, key: str, context: Any | None = None) -> str:
        """Generate a unique cache key based on key and context."""
        scope_suffix = "global"
        if context:
            user = getattr(context, "user", None) or getattr(
                getattr(context, "state", None),
                "user",
                None,
            )
            # Use canonical `user_id` when present
            if user and hasattr(user, "user_id"):
                scope_suffix = f"user:{user.user_id}"
        return f"settings:resolved:{key}:{scope_suffix}"

    async def _get_from_repo(
        self,
        key: str,
        scope: str,
        scope_id: str,
    ) -> str | None:
        """Fetch raw value from repository using simple filters."""
        try:
            # Using simple filter-based find_one
            setting = await self.repo.find_one(scope=scope, scope_id=scope_id, key=key)
            return setting.value if setting else None
        except BaseException:
            logger.exception("Failed to fetch setting %s from repo", key)
            return None

    def _cast_value(self, value: str, definition: SettingDefinition | None) -> Any:
        # ... (rest of the method unchanged)
        if not definition:
            return value

        if definition.type == "bool":
            return value.lower() == "true"
        if definition.type == "int":
            try:
                return int(value)
            except ValueError:
                return 0
        elif definition.type == "json":
            from lexigram.serialization import loads_str

            try:
                return loads_str(value)
            except (json.JSONDecodeError, ValueError, TypeError) as e:
                logger.warning(
                    "Failed to parse JSON setting for %s: %s",
                    definition.key,
                    e,
                )
                return {}

        return value

    async def set(
        self,
        key: str,
        value: Any,
        scope: str = "global",
        scope_id: str = "system",
        context: Any | None = None,
    ) -> Any:
        """Persist a setting value with audit tracking and cache invalidation."""

        # 1. Resolve Auditor
        updated_by = None
        if context:
            user = getattr(context, "user", None) or getattr(
                getattr(context, "state", None),
                "user",
                None,
            )
            if user:
                # Prefer username, then canonical user_id, then fallback to str(user)
                updated_by = getattr(
                    user,
                    "username",
                    getattr(user, "user_id", str(user)),
                )

        # 2. Type serialization
        str_value = str(value)
        if isinstance(value, bool):
            str_value = "true" if value else "false"
        elif isinstance(value, (dict, list)):
            from lexigram.serialization import dumps_str

            str_value = dumps_str(value)

        definition = self.registry.get(key)
        setting_type = "string"
        is_sensitive = False

        if definition:
            setting_type = definition.type
            is_sensitive = definition.type == "secret"
        else:
            # Fallback to ConfigRegistry
            try:
                from lexigram.admin.lib.di import get_admin_resolver
                from lexigram.admin.settings.panel.registry import ConfigRegistry

                resolver = get_admin_resolver(context)
                config_registry = await resolver.resolve(
                    ConfigRegistry,
                )
                node = config_registry.get_node(key)
                if node:
                    setting_type = map_config_node_type(node)
                    is_sensitive = setting_type == "secret"
            except ImportError:
                _warn_registry_unavailable()

        try:
            existing = await self.repo.find_one(scope=scope, scope_id=scope_id, key=key)

            if existing:
                existing.value = str_value
                existing.updated_at = datetime.now(UTC)
                existing.updated_by = updated_by
                await self.repo.update(existing)
            else:
                new_setting = SystemSetting(
                    scope=scope,
                    scope_id=scope_id,
                    key=key,
                    value=str_value,
                    type=setting_type,
                    is_sensitive=is_sensitive,
                    updated_by=updated_by,
                )
                await self.repo.create(new_setting)

            # 3. Invalidate Cache
            if self.cache:
                await self.cache.delete(f"settings:resolved:{key}:global")
                if scope == "user":
                    await self.cache.delete(f"settings:resolved:{key}:user:{scope_id}")

            # Fire Event
            if self.event_bus:
                try:
                    await self.event_bus.publish(
                        SettingUpdated(
                            key=key,
                            value=str_value,
                            scope=scope,
                            scope_id=scope_id,
                        ),
                    )
                except BaseException:
                    logger.exception("Failed to publish SettingUpdated event")

        except BaseException:
            logger.exception("Failed to save setting %s", key)
            raise

    async def get_all_resolved(self, context: Any | None = None) -> dict[str, Any]:
        """Return a dictionary of all resolved settings for the current context."""
        settings = {}
        for definition in self.registry.get_all():
            settings[definition.key] = await self.get(definition.key, context)
        return settings

    async def boot(self, container: ContainerResolverProtocol | None = None) -> None:
        """Initialize settings resources and register as Config Store."""
        # Register as a store for ConfigRegistry
        from lexigram.admin.lib.di import get_admin_resolver
        from lexigram.admin.settings.panel.registry import ConfigRegistry, StoreBase

        resolver = get_admin_resolver(container)
        registry = await resolver.resolve(ConfigRegistry)

        class SettingsServiceStore(StoreBase):
            def __init__(self, service: SettingsService):
                self.service = service

            async def get(self, key: str, default: Any = None) -> Any:
                val = await self.service.get(key)
                return val if val is not None else default

            async def set(self, key: str, value: Any) -> None:
                await self.service.set(key, value)

        # Register store named 'app' (matches ConfigSpec category 'app' if we map it)
        # But ConfigRegistry uses store_name="default" by default.
        # We should register it as 'db' or override 'default'?
        # For now, let's register as 'default' to take over persistence globally
        # (since MemoryStore is useless in production)
        registry.register_store("default", SettingsServiceStore(self))

        logger.info("✓ SettingsService registered as default ConfigRegistry store")

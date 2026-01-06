"""Feature flags service for lexigram-admin.

Provides :class:`AdminFeatureFlagService` — a thin admin-specific wrapper
around :class:`~lexigram.contracts.feature_flags.protocols.FlagManagerProtocol`
that enforces the ``admin.`` namespace prefix and exposes admin-specific
decorators and helpers.

FWK-03: AdminFeatureFlagService implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import wraps
from typing import Any

from lexigram.contracts.exceptions import ConfigurationError, InfrastructureError
from lexigram.contracts.feature_flags.protocols import FlagManagerProtocol
from lexigram.di.decorators import inject

# ============================================================================
# Admin Feature Flag Configuration
# ============================================================================


@dataclass
class AdminFeatureConfig:
    """Configuration for admin features.

    Each boolean field represents a feature that can be toggled.
    """

    # Core features
    soft_delete: bool = True
    audit_logging: bool = True
    bulk_operations: bool = True
    export_data: bool = True
    import_data: bool = True

    # UI features
    dark_mode: bool = True
    sidebar_collapse: bool = True
    table_column_resize: bool = True
    inline_editing: bool = False

    # Advanced features
    custom_dashboards: bool = False
    api_explorer: bool = False
    webhook_management: bool = False
    scheduled_tasks: bool = False

    # Beta features
    ai_assistant: bool = False
    predictive_search: bool = False


# ============================================================================
# Admin Feature Flag Service
# ============================================================================


@inject
class AdminFeatureFlagService:
    """Feature flag service for the admin panel.

    Delegates flag evaluation to a FlagManager while enforcing the ``admin.``
    prefix namespace and seeding initial values from :class:`AdminFeatureConfig`.

    The manager implementation is supplied through DI via contracts.

    Example::

        service = AdminFeatureFlagService(manager, AdminFeatureConfig())
        if await service.is_enabled("soft_delete"):
            ...
    """

    def __init__(
        self,
        manager: FlagManagerProtocol,
        config: AdminFeatureConfig | None = None,
    ) -> None:
        """Initialize the service.

        Args:
            manager: Feature flag manager whose provider is a LocalProvider.
                Requires ``lexigram-features`` to be installed.
            config: Optional configuration controlling initial flag values.
                Defaults to :class:`AdminFeatureConfig`.

        Raises:
            InfrastructureError: If no feature-flag manager binding is available.
        """
        if manager is None:
            raise InfrastructureError(
                "AdminFeatureFlagService requires a FlagManagerProtocol binding.",
            )
        self._manager = manager
        self._config = config or AdminFeatureConfig()
        self._register_config_flags(self._config)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _normalize(self, flag_name: str) -> str:
        """Ensure *flag_name* carries the ``admin.`` prefix."""
        if not flag_name.startswith("admin."):
            return f"admin.{flag_name}"
        return flag_name

    def _register_config_flags(self, config: AdminFeatureConfig) -> None:
        """Validate feature configuration payload shape."""
        for field_name in config.__dataclass_fields__:
            if not isinstance(getattr(config, field_name), bool):
                msg = f"AdminFeatureConfig field '{field_name}' must be bool."
                raise ConfigurationError(msg)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def is_enabled_sync(
        self,
        flag_name: str,
        context: dict[str, Any] | None = None,
        default: bool = False,
    ) -> bool:
        """Synchronously check whether a feature flag is enabled.

        Safe to call outside an async context because the backing store is
        always in-memory.  For the async primary, use :meth:`is_enabled`.

        Args:
            flag_name: Flag name (with or without the ``admin.`` prefix).
            context: Optional evaluation context.
            default: Fallback value when the flag is not found.

        Returns:
            True if the flag is enabled.
        """
        flag_name = self._normalize(flag_name)
        short_name = flag_name.removeprefix("admin.")
        if short_name in self._config.__dataclass_fields__:
            return bool(getattr(self._config, short_name))
        return default

    async def is_enabled(
        self,
        flag_name: str,
        context: dict[str, Any] | None = None,
        default: bool = False,
    ) -> bool:
        """Check if a feature flag is enabled (async primary).

        Args:
            flag_name: Flag name (with or without the ``admin.`` prefix).
            context: Optional evaluation context.
            default: Fallback value when the flag is not found.

        Returns:
            True if the flag is enabled.
        """
        flag_name = self._normalize(flag_name)
        value = await self._manager.get_value(flag_name, default, context=context)
        return bool(value)

    def set_flag(self, flag_name: str, enabled: bool) -> None:
        """Set a feature flag value.

        Args:
            flag_name: Flag name (with or without the ``admin.`` prefix).
            enabled: Whether the flag should be enabled.
        """
        raise ConfigurationError(
            "AdminFeatureFlagService.set_flag() is unsupported in contract-only mode. "
            "Set flags via your configured FlagManagerProtocol provider.",
        )

    async def get_all_flags(self) -> dict[str, bool]:
        """Return all admin feature flags.

        Returns:
            Mapping of short names (without ``admin.`` prefix) to enabled state.
        """
        all_flags = await self._manager.get_all_flags()
        result: dict[str, bool] = {}
        for key, evaluation in all_flags.items():
            if key.startswith("admin."):
                result[key.removeprefix("admin.")] = bool(evaluation.value)
        return result

    def require_flag(self, flag_name: str) -> None:
        """Raise if a flag is not enabled.

        Args:
            flag_name: Flag to check.

        Raises:
            FeatureDisabledError: If the flag is not enabled.
        """
        if not self.is_enabled_sync(flag_name):
            raise FeatureDisabledError(flag_name)

    def get_variant(
        self,
        flag_name: str,
        context: dict[str, Any] | None = None,
        default: str = "",
    ) -> str:
        """Return the variant string for a VARIANT-type flag.

        Args:
            flag_name: Flag name (with or without the ``admin.`` prefix).
            context: Optional evaluation context.
            default: Fallback value when no variant is stored.

        Returns:
            The variant string or *default*.
        """
        _ = self._normalize(flag_name)
        _ = context
        return default


# ============================================================================
# Module-level helpers
# ============================================================================


async def get_feature_flag_service(
    context: Any | None = None,
) -> AdminFeatureFlagService:
    """Resolve the admin feature flag service from the DI container."""
    from lexigram.admin.lib.di import get_admin_resolver

    resolver = get_admin_resolver(context)
    return await resolver.resolve(AdminFeatureFlagService)


def __getattr__(name: str) -> Any:
    if name == "feature_flag_service":
        raise AttributeError(
            "feature_flag_service is now async. Use: await get_feature_flag_service()",
        )
    raise AttributeError(f"module {__name__} has no attribute {name}")


# ============================================================================
# Admin-specific exception
# ============================================================================


class FeatureDisabledError(ConfigurationError):
    """Raised when a required admin feature is disabled."""

    _code: str = "LEX_ERR_ADMIN_027"

    def __init__(self, flag_name: str) -> None:
        self.flag_name = flag_name
        super().__init__(
            f"Feature '{flag_name}' is disabled",
            details={"flag_name": flag_name},
        )


# ============================================================================
# Admin-specific decorators and helpers
# ============================================================================


def require_feature(flag_name: str) -> Any:
    """Decorator: raise :class:`FeatureDisabledError` if *flag_name* is disabled.

    Example::

        @require_feature("bulk_operations")
        async def bulk_delete(request):
            ...
    """

    def decorator(func) -> Any:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            service = await get_feature_flag_service()
            service.require_flag(flag_name)
            return await func(*args, **kwargs)

        return wrapper

    return decorator


async def feature_enabled(flag_name: str, default: bool = False) -> bool:
    """Check if an admin feature flag is enabled.

    Example::

        if await feature_enabled("dark_mode"):
            ...
    """
    service = await get_feature_flag_service()
    return await service.is_enabled(flag_name, default=default)


__all__ = [
    "AdminFeatureConfig",
    "AdminFeatureFlagService",
    "FeatureDisabledError",
    "feature_enabled",
    "require_feature",
]

"""AuditModule — IoC module for the Lexigram audit subsystem."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.audit import AuditLoggerProtocol, AuditStoreProtocol
from lexigram.di.module import DynamicModule, module

if TYPE_CHECKING:
    from lexigram.audit.config import AuditConfig

__all__ = ["AuditModule"]


@module(is_global=True)
class AuditModule:
    """Lexigram audit module.

    Global like ``EventsModule``/``QueueModule`` so any consumer module
    (e.g. an app's infrastructure provider) can resolve audit protocols
    without declaring explicit imports.

    Registers the full audit stack including store, logger, retention,
    verification, and optional admin panel contributor.

    Usage::

        app = Application()
        app.use(AuditModule.configure(
            hmac_key=b"secret",
            retention_days=365,
        ))

    Or with an explicit :class:`~lexigram.audit.config.AuditConfig` section::

        app.use(AuditModule.configure(config=AuditConfig(store_backend="memory")))
    """

    @classmethod
    def configure(
        cls,
        config: AuditConfig | None = None,
        *,
        hmac_key: bytes | None = None,
        store_backend: str | None = None,
        table_name: str | None = None,
        retention_days: int | None = None,
        enable_admin: bool = True,
        **overrides: Any,
    ) -> DynamicModule:
        """Configure the audit module.

        Args:
            config: Explicit :class:`~lexigram.audit.config.AuditConfig`
                section. When provided it wins over the keyword shortcuts
                below.
            hmac_key: HMAC key for checksum computation.
            store_backend: ``"sql"`` or ``"memory"``.
            table_name: SQL table name.
            retention_days: Default retention in days.
            enable_admin: Register admin contributor.
            **overrides: Additional AuditConfig fields.

        Returns:
            DynamicModule ready for ``app.use()``.

        Note:
            Called with no arguments, the module passes ``None`` through so
            the orchestrator injects the typed ``audit`` yaml section before
            registration (framework defaults apply when no section exists).
        """
        from lexigram.audit.config import AuditConfig
        from lexigram.audit.di.bundle_provider import AuditBundleProvider
        from lexigram.contracts.audit import RetentionPolicy

        if config is None and (
            hmac_key is not None
            or store_backend is not None
            or table_name is not None
            or retention_days is not None
            or overrides
        ):
            config = AuditConfig(
                store_backend=store_backend or "sql",
                table_name=table_name or "audit_log",
                hmac_key=hmac_key,
                retention_policy=RetentionPolicy(
                    name="default",
                    default_retention_days=retention_days or 365,
                ),
                enable_admin=enable_admin,
                **overrides,
            )
        return DynamicModule(
            module=cls,
            providers=[AuditBundleProvider(config=config, enable_admin=enable_admin)],
            exports=[AuditLoggerProtocol, AuditStoreProtocol],
        )

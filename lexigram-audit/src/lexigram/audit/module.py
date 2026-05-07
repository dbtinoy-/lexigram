"""AuditModule — IoC module for the Lexigram audit subsystem."""

from __future__ import annotations

from typing import Any

from lexigram.contracts.audit import AuditLoggerProtocol, AuditStoreProtocol
from lexigram.di.module import DynamicModule, module

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
    """

    @classmethod
    def configure(
        cls,
        *,
        hmac_key: bytes | None = None,
        store_backend: str = "sql",
        table_name: str = "audit_log",
        retention_days: int = 365,
        enable_admin: bool = True,
        **overrides: Any,
    ) -> DynamicModule:
        """Configure the audit module.

        Args:
            hmac_key: HMAC key for checksum computation.
            store_backend: ``"sql"`` or ``"memory"``.
            table_name: SQL table name.
            retention_days: Default retention in days.
            enable_admin: Register admin contributor.
            **overrides: Additional AuditConfig fields.

        Returns:
            DynamicModule ready for ``app.use()``.
        """
        from lexigram.audit.config import AuditConfig
        from lexigram.audit.di.bundle_provider import AuditBundleProvider
        from lexigram.contracts.audit import RetentionPolicy

        config = AuditConfig(
            store_backend=store_backend,
            table_name=table_name,
            hmac_key=hmac_key,
            retention_policy=RetentionPolicy(
                name="default",
                default_retention_days=retention_days,
            ),
            enable_admin=enable_admin,
        )
        return DynamicModule(
            module=cls,
            providers=[AuditBundleProvider(config=config, enable_admin=enable_admin)],
            exports=[AuditLoggerProtocol, AuditStoreProtocol],
        )

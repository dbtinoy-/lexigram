"""CLI shell context factories for lexigram-audit."""

from __future__ import annotations

from typing import TYPE_CHECKING

from lexigram.audit.logging.logger import AuditLogger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import ContainerResolverProtocol


async def provide_audit_logger(container: ContainerResolverProtocol) -> AuditLogger:
    """Provide audit logger for interactive shell use.

    Args:
        container: Booted DI container.

    Returns:
        The resolved audit logger instance.
    """
    return await container.resolve(AuditLogger)

"""AuditScheduler: registers and schedules the audit verifier task.

Implements ``AuditVerifierSchedulerProtocol`` from
``lexigram.contracts.observability.audit`` so that extension packages
(e.g. ``lexigram-admin``) can schedule audit verification without
importing concrete implementation details.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.audit import AuditVerifierProtocol
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.audit.config import AuditConfig

logger = get_logger(__name__)

__all__ = ["AuditScheduler"]


class AuditScheduler:
    """Registers and schedules the audit verifier task via a task provider.

    Satisfies ``AuditVerifierSchedulerProtocol`` from
    ``lexigram.contracts.observability.audit`` without requiring callers
    to import anything from ``lexigram-sql``.

    Args:
        verifier: Audit verifier used to check recent entries.
        config: Audit configuration (provides schedule and batch size).
    """

    def __init__(
        self,
        verifier: AuditVerifierProtocol,
        config: AuditConfig,
    ) -> None:
        self._verifier = verifier
        self._config = config

    # ------------------------------------------------------------------
    # AuditVerifierSchedulerProtocol
    # ------------------------------------------------------------------

    def register_handler(self, task_provider: Any) -> None:
        """Register the audit verifier handler with a task provider.

        Creates an async handler that calls ``verify_recent`` on the
        injected verifier and logs any detected mismatches.

        Args:
            task_provider: A task provider that exposes ``register_handler``.
        """
        verifier = self._verifier
        batch_size = self._config.verification_batch_size

        async def _handler(*args: Any, **kwargs: Any) -> Any:
            mismatches = await verifier.verify_recent(limit=batch_size)
            if mismatches:
                logger.warning(
                    "audit.verify_recent.mismatches_detected",
                    count=len(mismatches),
                )
                for m in mismatches:
                    logger.debug("audit.verify_recent.mismatch", mismatch=m)
            return {"mismatches": mismatches}

        try:
            task_provider.register_handler("audit:verify_recent", _handler)
        except (RuntimeError, ValueError, TypeError, AttributeError) as exc:
            logger.debug("audit_handler_registration_suppressed", error=str(exc))

    def schedule(
        self,
        task_provider: Any,
        *,
        audit_table: str = "audit_log",
        key: bytes | None = None,
    ) -> str | None:
        """Schedule the periodic audit verifier job.

        Args:
            task_provider: A task provider/scheduler with ``schedule_job``.
            audit_table: Name of the audit table (passed through for compatibility).
            key: HMAC key (passed through for compatibility).

        Returns:
            Job ID returned by the scheduler, or ``None``.
        """
        try:
            return task_provider.schedule_job(
                "audit:verify_recent",
                self._config.verification_schedule,
            )
        except (AttributeError, TypeError, ValueError, RuntimeError) as exc:
            logger.debug("audit_schedule_failed", error=str(exc))
            return None

"""AuditedAction — framework base class that wraps execute() with audit logging.

Subclasses extend both AuditedAction and a concrete Action subclass
(RowAction, BulkAction, HeaderAction).  The abstract method is
execute_audited(); the inherited execute() is sealed here.

Writes are made through ctx.audit_writer.  If audit_writer is None,
execution proceeds and a warning is logged (best-effort at framework level).
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any, Generic, TypeVar

from lexigram.admin.actions.base import Action
from lexigram.admin.actions.exceptions import ActionError
from lexigram.admin.actions.types import ActionContext
from lexigram.contracts.admin.audit_entry import AuditEntry, AuditOutcome
from lexigram.logging import get_logger
from lexigram.result import Result

logger = get_logger(__name__)

_RT = TypeVar("_RT")
_OT = TypeVar("_OT")


class AuditedAction(Action[_RT, _OT], Generic[_RT, _OT]):
    """Action base that wraps execute() with before/after audit capture.

    Subclass together with a concrete Action specialisation:

        class DeleteUser(AuditedAction[User, None], RowAction):
            name = "delete_user"
            resource_type = "users"

            async def execute_audited(self, record, ctx):
                ...

    Attributes:
        resource_type: The resource category recorded in the audit entry.
            Must be set by each subclass.
    """

    resource_type: str = ""

    @abstractmethod
    async def execute_audited(
        self, record_or_records: _RT, ctx: ActionContext
    ) -> Result[_OT, ActionError]:
        ...

    def capture_before(self, record: _RT) -> dict[str, Any] | None:
        return None

    def capture_after(self, record: _RT, outcome: _OT) -> dict[str, Any] | None:
        return None

    def resource_id_of(self, record: _RT) -> str:
        if record is None:
            return ""
        if isinstance(record, dict):
            return str(record.get("id", ""))
        return str(getattr(record, "id", record))

    async def execute(
        self, record_or_records: _RT, ctx: ActionContext
    ) -> Result[_OT, ActionError]:
        """Sealed execute() — wraps execute_audited() with audit writes."""
        before_snapshot = self.capture_before(record_or_records)

        result = await self.execute_audited(record_or_records, ctx)

        outcome_value: AuditOutcome
        after_snapshot: dict[str, Any] = {}

        if result.is_ok():
            outcome_value = AuditOutcome.SUCCESS
            raw_after = self.capture_after(record_or_records, result.unwrap())
            if raw_after is not None:
                after_snapshot = raw_after
        else:
            outcome_value = AuditOutcome.ERRORED

        admin_user_id = ""
        if ctx.user is not None:
            admin_user_id = str(
                getattr(ctx.user, "user_id", None)
                or getattr(ctx.user, "id", None)
                or ""
            )

        resource_id = ctx.record_id or self.resource_id_of(record_or_records)

        entry = AuditEntry(
            admin_user_id=admin_user_id,
            action=self.name,
            resource_type=self.resource_type or ctx.resource_name,
            resource_id=resource_id or None,
            outcome=outcome_value,
            before=before_snapshot or {},
            after=after_snapshot,
            correlation_id=ctx.correlation_id,
            request_id=ctx.request_id,
            request_ip=ctx.request_ip,
            metadata=dict(ctx.metadata),
        )

        writer = ctx.audit_writer
        if writer is None:
            logger.warning(
                "admin.audited_action_no_writer",
                action=self.name,
                resource_type=self.resource_type,
            )
        else:
            await writer.write(entry)

        return result


__all__ = ["AuditedAction"]

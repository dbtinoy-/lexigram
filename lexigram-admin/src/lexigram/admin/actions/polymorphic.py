"""PolymorphicBulkAction — dispatches bulk records to per-type action handlers.

.. stability:: stable

Usage::

    class MarkReviewedBulkAction(PolymorphicBulkAction):
        name = "mark_reviewed"
        handlers: ClassVar[dict[type, Action[Any, Any]]] = {
            AIAnalysis: MarkAIAnalysisReviewedAction(name="mark_reviewed"),
            VetSubmission: MarkVetSubmissionReviewedAction(name="mark_reviewed"),
        }

The ``handlers`` map is a ``ClassVar`` (not a dataclass field) so that
``dict`` values are not subject to frozen-dataclass hash requirements.
First ``isinstance`` match wins for each record.
"""

from __future__ import annotations

from typing import Any, ClassVar

from lexigram.admin.actions.base import Action, BulkAction
from lexigram.admin.actions.exceptions import ActionError
from lexigram.admin.actions.types import ActionContext
from lexigram.result import Err, Ok, Result


class PolymorphicBulkAction(BulkAction):
    """Bulk action that dispatches records to per-type handler instances.

    Subclasses declare a ``handlers`` class variable mapping record types
    to ``Action`` instances.  On ``execute()``, each record in the input
    list is matched against the handlers map via ``isinstance`` (first
    match wins).  Records that match no handler cause the action to return
    ``Err``.  If any handler returns ``Err``, the overall result is ``Err``.

    Attributes:
        handlers: Class-level mapping of record type → Action handler.
    """

    handlers: ClassVar[dict[type, Action[Any, Any]]] = {}

    async def execute(
        self,
        record_or_records: list[Any],
        ctx: ActionContext,
    ) -> Result[Any, ActionError]:
        outcomes: list[Any] = []

        for record in record_or_records:
            handler: Action[Any, Any] | None = None
            for record_type, candidate in self.handlers.items():
                if isinstance(record, record_type):
                    handler = candidate
                    break

            if handler is None:
                return Err(
                    ActionError(
                        f"No handler registered for record type "
                        f"'{type(record).__name__}' in {type(self).__name__}"
                    )
                )

            result = await handler.execute(record, ctx)
            if result.is_err():
                return result
            outcomes.append(result.unwrap())

        return Ok(outcomes)


__all__ = ["PolymorphicBulkAction"]

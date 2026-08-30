"""Relation actions for relation managers (associate, attach, detach, dissociate).

These actions drive relation-manager operations from the action layer.
Pivot-based operations
(associate/attach/detach) require a :class:`BelongsToManyRelationManager`
configured with a pivot table and an attached data source; they fail
with an :class:`ActionError` otherwise.
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.actions.base import RowAction
from lexigram.admin.actions.exceptions import ActionError
from lexigram.admin.actions.types import ActionColor, ActionContext
from lexigram.admin.relations.belongs_to_many import BelongsToManyRelationManager
from lexigram.result import Err, Ok, Result


class _RelationAction(RowAction):
    """Base class for relation actions.

    Resolves the target relation manager from the constructor or from
    ``ctx.metadata["relation_manager"]``.
    """

    def __init__(
        self,
        name: str,
        label: str,
        icon: str,
        color: ActionColor,
        relation_manager: Any = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(name=name, label=label, icon=icon, color=color, **kwargs)
        self._relation_manager = relation_manager

    def _resolve_manager(self, ctx: ActionContext) -> Result[Any, ActionError]:
        """Resolve the relation manager for this action."""
        manager = self._relation_manager or ctx.metadata.get("relation_manager")
        if manager is None:
            return Err(
                ActionError(
                    "Relation action requires a relation manager; inject one "
                    "or set ctx.metadata['relation_manager']."
                )
            )
        return Ok(manager)


class AssociateAction(_RelationAction):
    """Associate an existing related record with the parent.

    Attaches a related record through the relation manager's pivot
    store. The related record ID comes from ``related_id``, from
    ``ctx.metadata["related_id"]``, or from the record's ``id``.
    """

    def __init__(
        self,
        name: str = "associate",
        label: str | None = None,
        relation_manager: Any = None,
        related_id: str | None = None,
        pivot_data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Associate",
            icon="link",
            color=ActionColor.PRIMARY,
            relation_manager=relation_manager,
            **kwargs,
        )
        self._related_id = related_id
        self._pivot_data = pivot_data

    async def execute(
        self, record: Any, ctx: ActionContext
    ) -> Result[Any, ActionError]:
        resolved = self._resolve_manager(ctx)
        if resolved.is_err():
            return Err(resolved.unwrap_err())
        manager = resolved.unwrap()

        related_id = self._related_id or ctx.metadata.get("related_id")
        if related_id is None and isinstance(record, dict):
            related_id = record.get("id")
        if related_id is None:
            return Err(
                ActionError(
                    "AssociateAction requires a related_id; pass one to the "
                    "action or set ctx.metadata['related_id']."
                )
            )

        if not isinstance(manager, BelongsToManyRelationManager):
            return Err(
                ActionError(
                    f"Relation manager {type(manager).__name__} does not support "
                    "associate; use a BelongsToManyRelationManager."
                )
            )

        pivot_data = self._pivot_data or ctx.metadata.get("pivot_data")
        await manager.attach(related_id, pivot_data)
        return Ok(
            {
                "message": f"Associated {related_id}",
                "related_id": related_id,
                "action": "associate",
            }
        )


class AttachAction(AssociateAction):
    """Attach an existing related record to the parent with optional pivot data.

    Executes the same pivot attach as :class:`AssociateAction` under a
    distinct name/label.
    """

    def __init__(
        self,
        name: str = "attach",
        label: str | None = None,
        relation_manager: Any = None,
        related_id: str | None = None,
        pivot_data: dict[str, Any] | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Attach",
            relation_manager=relation_manager,
            related_id=related_id,
            pivot_data=pivot_data,
            **kwargs,
        )


class DetachAction(_RelationAction):
    """Detach a related record from the parent (removes pivot rows)."""

    def __init__(
        self,
        name: str = "detach",
        label: str | None = None,
        relation_manager: Any = None,
        related_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Detach",
            icon="unlink",
            color=ActionColor.WARNING,
            relation_manager=relation_manager,
            **kwargs,
        )
        self._related_id = related_id

    async def execute(
        self, record: Any, ctx: ActionContext
    ) -> Result[Any, ActionError]:
        resolved = self._resolve_manager(ctx)
        if resolved.is_err():
            return Err(resolved.unwrap_err())
        manager = resolved.unwrap()

        related_id = self._related_id or ctx.metadata.get("related_id")
        if related_id is None and isinstance(record, dict):
            related_id = record.get("id")
        if related_id is None:
            return Err(
                ActionError(
                    "DetachAction requires a related_id; pass one to the "
                    "action or set ctx.metadata['related_id']."
                )
            )

        if not isinstance(manager, BelongsToManyRelationManager):
            return Err(
                ActionError(
                    f"Relation manager {type(manager).__name__} does not support "
                    "detach; use a BelongsToManyRelationManager."
                )
            )

        await manager.detach(related_id)
        return Ok(
            {
                "message": f"Detached {related_id}",
                "related_id": related_id,
                "action": "detach",
            }
        )


class DissociateAction(_RelationAction):
    """Remove the relation to a record without deleting the record itself.

    Works with any relation manager exposing a ``detach`` operation;
    fails with an :class:`ActionError` when the manager has none.
    """

    def __init__(
        self,
        name: str = "dissociate",
        label: str | None = None,
        relation_manager: Any = None,
        related_id: str | None = None,
        **kwargs: Any,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Dissociate",
            icon="unlink",
            color=ActionColor.WARNING,
            relation_manager=relation_manager,
            **kwargs,
        )
        self._related_id = related_id

    async def execute(
        self, record: Any, ctx: ActionContext
    ) -> Result[Any, ActionError]:
        resolved = self._resolve_manager(ctx)
        if resolved.is_err():
            return Err(resolved.unwrap_err())
        manager = resolved.unwrap()

        related_id = self._related_id or ctx.metadata.get("related_id")
        if related_id is None and isinstance(record, dict):
            related_id = record.get("id")
        if related_id is None:
            return Err(
                ActionError(
                    "DissociateAction requires a related_id; pass one to the "
                    "action or set ctx.metadata['related_id']."
                )
            )

        detach = getattr(manager, "detach", None)
        if detach is None:
            return Err(
                ActionError(
                    f"Relation manager {type(manager).__name__} does not support "
                    "dissociate; no detach operation available."
                )
            )

        await detach(related_id)
        return Ok(
            {
                "message": f"Dissociated {related_id}",
                "related_id": related_id,
                "action": "dissociate",
            }
        )


__all__ = [
    "AssociateAction",
    "AttachAction",
    "DetachAction",
    "DissociateAction",
]

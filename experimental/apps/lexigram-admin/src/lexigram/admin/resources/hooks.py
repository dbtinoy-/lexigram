"""Lifecycle and action hook helpers for Admin Resources.

Default ``before_*`` / ``after_*`` record hooks plus the action lifecycle
hook attachment point. Composed into
:class:`~lexigram.admin.resources.base.Resource` via inheritance so the
hooks remain part of every resource's public surface. Subclasses override
to customise behaviour.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.domain import DomainModel


class ResourceHooksMixin:
    """Record lifecycle hooks and the action hook attachment point.

    Requires the composing class to provide a ``model`` attribute
    (defined by :class:`~lexigram.admin.resources.base.Resource`).
    """

    model: type[DomainModel] | None

    async def before_create(self, data: dict) -> dict:
        """Hook called before a record is created.

        Args:
            data: Record data to be created

        Returns:
            Modified data
        """
        return data

    async def before_validate(self, data: dict) -> Any:
        """Validate and coerce form data against the resource model.

        Base implementation coerces HTML form strings to proper Python types
        via _coerce_form_data, then validates against ``self.model``.
        Returns Ok(coerced_data) on success, Err(AdminValidationError) with
        per-field errors on failure.

        Override in subclasses to add custom validation logic.
        """
        from lexigram.admin.exceptions import AdminValidationError
        from lexigram.admin.resources.form_coercion import _coerce_form_data
        from lexigram.contracts.exceptions.domain import FieldError
        from lexigram.result import Err, Ok

        coerced = _coerce_form_data(data, self.model)
        if self.model is None:
            return Ok(coerced)

        if not hasattr(self.model, "model_validate"):
            return Ok(coerced)

        try:
            self.model.model_validate(coerced)
        except (ValueError, TypeError) as exc:
            msg = str(exc)
            errors: list[FieldError] = []

            is_pydantic = (
                type(exc).__name__ == "ValidationError"
                and "pydantic" in type(exc).__module__
            )
            if is_pydantic:
                for err in exc.errors():  # type: ignore[union-attr]
                    field = str(err["loc"][0]) if err.get("loc") else None
                    if field and field in coerced:
                        errors.append(FieldError(field=field, message=err["msg"]))
            else:
                field = None
                if msg.startswith("Field '"):
                    field = msg.split("'")[1]
                if field:
                    errors.append(FieldError(field=field, message=msg))

            if errors:
                return Err(
                    AdminValidationError(
                        message="Form validation failed",
                        errors=errors,
                    )
                )
            return Ok(coerced)

        return Ok(coerced)

    async def after_create(self, record: Any) -> None:
        """Hook called after a record is created.

        Args:
            record: Created record
        """

    async def before_update(self, item_id: Any, data: dict) -> dict:
        """Hook called before a record is updated.

        Args:
            item_id: Record identifier
            data: Updated record data

        Returns:
            Modified data
        """
        return data

    async def after_update(self, record: Any) -> None:
        """Hook called after a record is updated.

        Args:
            record: Updated record
        """

    async def before_delete(self, item_id: Any) -> None:
        """Hook called before a record is deleted.

        Args:
            item_id: Record identifier
        """

    async def after_delete(self, item_id: Any) -> None:
        """Hook called after a record is deleted.

        Args:
            item_id: Record identifier
        """

    @classmethod
    def get_action_hooks(cls, action_name: str) -> list[Any]:
        """Get action lifecycle hooks for the named action.

        Override in a resource subclass to attach ``ActionHookProtocol``
        hooks to registry-based actions. Hooks are collected by
        ``ActionExecutor`` and run before/after the action body and on
        failure.

        Args:
            action_name: Name of the action (e.g. ``"export"``)

        Returns:
            List of action hooks for the action.
        """
        return []


__all__ = ["ResourceHooksMixin"]

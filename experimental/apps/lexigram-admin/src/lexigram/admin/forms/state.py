"""Unified Form State Management."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any


@dataclass
class FormState:
    """Manages the state of a form, including values and errors."""

    data: dict[str, Any] = field(default_factory=dict)
    errors: dict[str, list[str]] = field(default_factory=dict)
    is_dirty: bool = False
    is_submitting: bool = False
    last_saved_at: datetime | None = None

    def update_field(self, name: str, value: Any) -> Any:
        """Update a field's value and mark as dirty."""
        self.data[name] = value
        self.is_dirty = True

    def set_error(self, name: str, error: str) -> Any:
        """Set an error for a field."""
        if name not in self.errors:
            self.errors[name] = []
        self.errors[name].append(error)

    def clear_errors(self, name: str | None = None) -> Any:
        """Clear errors for a specific field or all fields."""
        if name:
            self.errors.pop(name, None)
        else:
            self.errors.clear()

    @property
    def has_errors(self) -> bool:
        """Check if any field has errors."""
        return len(self.errors) > 0

    def to_dict(self) -> dict[str, Any]:
        """Convert state to a dictionary for persistence."""
        return {
            "data": self.data,
            "errors": self.errors,
            "is_dirty": self.is_dirty,
            "last_saved_at": self.last_saved_at.isoformat()
            if self.last_saved_at
            else None,
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> FormState:
        """Create state from a dictionary."""
        last_saved = data.get("last_saved_at")
        return cls(
            data=data.get("data", {}),
            errors=data.get("errors", {}),
            is_dirty=data.get("is_dirty", False),
            last_saved_at=datetime.fromisoformat(last_saved) if last_saved else None,
        )


class FormStore:
    """Orchestrates form state and validation logic."""

    def __init__(
        self,
        initial_values: dict[str, Any] | None = None,
        validation_engine: Any | None = None,
    ):
        self.state = FormState(data=initial_values or {})
        self.validation_engine = validation_engine

    @property
    def data(self) -> dict[str, Any]:
        return self.state.data

    @property
    def errors(self) -> dict[str, list[str]]:
        return self.state.errors

    @property
    def is_dirty(self) -> bool:
        return self.state.is_dirty

    def get_value(self, name: str, default: Any = None) -> Any:
        return self.data.get(name, default)

    def set_value(self, name: str, value: Any) -> Any:
        self.state.update_field(name, value)

    async def validate(self) -> bool:
        """Validate the current form data using the validation engine."""
        if not self.validation_engine:
            return True

        self.state.clear_errors()
        errors = await self.validation_engine.validate_form(self.data)

        if errors:
            for field_name, field_errors in errors.items():
                for error in field_errors:
                    msg = error.message if hasattr(error, "message") else str(error)
                    self.state.set_error(field_name, msg)
            return False

        return True

    def to_dict(self) -> dict[str, Any]:
        return self.state.to_dict()

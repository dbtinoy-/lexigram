"""Session state management for Lexigram Admin.

This module provides request-scoped session state storage via DI container.
"""

from __future__ import annotations

from collections.abc import ItemsView, KeysView, ValuesView
import contextvars
from typing import Any, ClassVar

from lexigram.di.decorators import inject
from lexigram.serialization import dumps_str, loads_str

# JSONEncoder removed, orjson handles these natively or via default


class SessionStateService:
    """Request-scoped session state service.

    Provides a dict-like interface for storing state within a single request.
    Automatically serializes complex types to JSON for persistence.
    """

    def __init__(self) -> None:
        """Initialize an empty session state."""
        self._data: dict[str, Any] = {}

    async def get(self, key: str, default: Any = None) -> Any:
        """Get a value from session state (async)."""
        return self._data.get(key, default)

    async def set(self, key: str, value: Any) -> None:
        """Set a value in session state (async)."""
        self._data[key] = value

    async def delete(self, key: str) -> None:
        """Delete a key from session state (async)."""
        if key in self._data:
            del self._data[key]
        else:
            raise KeyError(key)

    async def clear(self) -> None:
        """Clear all session state (async)."""
        self._data.clear()

    def keys(self) -> KeysView[str]:
        """Return all keys in session state."""
        return self._data.keys()

    def values(self) -> ValuesView[Any]:
        """Return all values in session state."""
        return self._data.values()

    def items(self) -> ItemsView[str, Any]:
        """Return all key-value pairs in session state."""
        return self._data.items()

    def __contains__(self, key: str) -> bool:
        """Check if a key exists in session state."""
        return key in self._data

    def __getitem__(self, key: str) -> Any:
        """Get a value using dict-like syntax."""
        return self._data[key]

    def __setitem__(self, key: str, value: Any) -> None:
        """Set a value using dict-like syntax."""
        self._data[key] = value

    def __delitem__(self, key: str) -> None:
        """Delete a value using dict-like syntax."""
        del self._data[key]

    def __len__(self) -> int:
        """Return the number of items in session state."""
        return len(self._data)

    def __repr__(self) -> str:
        """Return a string representation of session state."""
        return f"SessionStateService({self._data!r})"

    def to_json(self) -> str:
        """Serialize session state to JSON."""
        return dumps_str(self._data)

    def from_json(self, json_str: str) -> None:
        """Load session state from JSON."""
        self._data = loads_str(json_str)

    @property
    def is_empty(self) -> bool:
        """Check if session state is empty."""
        return len(self._data) == 0


@inject
class ActiveSessionContext:
    """Context manager for setting the active session using ContextVars."""

    _session_var: ClassVar[contextvars.ContextVar[SessionStateService | None]] = (
        contextvars.ContextVar("admin_request_session", default=None)
    )

    @classmethod
    def current(cls) -> SessionStateService | None:
        """Get the current active session from context variable."""
        return cls._session_var.get()

    def __init__(self, session: SessionStateService):
        self.session = session
        self._token = None

    def __enter__(self) -> SessionStateService:
        self._token = ActiveSessionContext._session_var.set(self.session)  # type: ignore[assignment]
        return self.session

    def __exit__(self, exc_type, exc_val, exc_tb) -> Any:
        if self._token:
            ActiveSessionContext._session_var.reset(self._token)

"""State persistence for Lexigram Admin."""

from __future__ import annotations

import contextlib
from typing import Any, Protocol

from lexigram import serialization as json
from lexigram.admin.state.store import Signal, watch


class IStorage(Protocol):
    """Protocol for storage backends."""

    def get(self, key: str) -> str | None: ...

    def set(self, key: str, value: str) -> None: ...

    def remove(self, key: str) -> None: ...


class DictionaryStorage(IStorage):
    """Memory-only storage for testing or server-side usage."""

    def __init__(self, initial_data: dict[str, str] | None = None) -> None:
        self._data = dict(initial_data or {})

    def get(self, key: str) -> str | None:
        return self._data.get(key)

    def set(self, key: str, value: str) -> None:
        self._data[key] = value

    def remove(self, key: str) -> None:
        self._data.pop(key, None)


class PersistedSignal(Signal[Any]):
    """A signal that automatically persists its value to a storage backend."""

    def __init__(self, key: str, initial_value: Any, storage: IStorage) -> None:
        self._key = key
        self._storage = storage

        # Try to load from storage
        stored_val = storage.get(key)
        if stored_val is not None:
            from lexigram.serialization import loads_str

            try:
                value = loads_str(stored_val)
            except (ValueError, TypeError, json.JSONDecodeError):
                value = initial_value
        else:
            value = initial_value

        super().__init__(value)

        # Set up auto-persistence
        @watch
        def _persist() -> Any:
            val = self.get()  # Register dependency
            from lexigram.serialization import dumps_str

            self._storage.set(self._key, dumps_str(val))


class StatePersistenceManager:
    """Manages persistence of multiple signals."""

    def __init__(self, storage: IStorage) -> None:
        self.storage = storage

    def persist(self, key: str, signal: Signal[Any]) -> None:
        """Add persistence to an existing signal."""
        # Load initial value
        stored_val = self.storage.get(key)
        if stored_val is not None:
            from lexigram.serialization import loads_str

            with contextlib.suppress(Exception):
                signal.set(loads_str(stored_val))

        # Watch for changes and save
        @watch
        def _save() -> Any:
            val = signal.get()
            from lexigram.serialization import dumps_str

            self.storage.set(key, dumps_str(val))

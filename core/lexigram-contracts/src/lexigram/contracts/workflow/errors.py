"""Workflow-domain exception classes.

Exceptions that cross extension-package boundaries live here so that core
``lexigram``, ``lexigram-workflow``, and all extension packages can import
them without cross-extension dependencies.
"""

from __future__ import annotations

from lexigram.contracts.exceptions.base import LexigramError


class SagaVersionMismatchError(LexigramError):
    """Raised when a persisted saga state version is incompatible with the current code.

    Attributes:
        saga_id: ID of the saga instance with the incompatible state.
        expected_version: The VERSION class attribute of the current saga class.
        stored_version: The version number found in the persisted state.
    """

    _code: str = "LEX_ERR_WF_009"

    def __init__(
        self,
        saga_id: str,
        expected_version: int,
        stored_version: int,
    ) -> None:
        super().__init__(
            f"Saga version mismatch for '{saga_id}': "
            f"expected v{expected_version}, stored v{stored_version}"
        )
        self.saga_id = saga_id
        self.expected_version = expected_version
        self.stored_version = stored_version


__all__ = [
    "SagaVersionMismatchError",
]

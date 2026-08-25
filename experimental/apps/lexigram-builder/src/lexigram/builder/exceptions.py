"""Typed errors for the builder package."""

from __future__ import annotations

from lexigram.contracts.exceptions.domain import DomainError


class BuilderError(DomainError):
    """Base error for all builder-domain failures."""

    _code = "LEX_ERR_BUILDER_001"

    def __init__(self, message: str = "Builder error", **kwargs: object) -> None:
        super().__init__(message, **kwargs)


class InvalidProjectNameError(BuilderError):
    """A project name failed identifier validation."""

    _code = "LEX_ERR_BUILDER_002"

    def __init__(self, message: str = "Invalid project name", **kwargs: object) -> None:
        super().__init__(message, **kwargs)


class ProjectNotFoundError(BuilderError):
    """The requested project does not exist on disk."""

    _code = "LEX_ERR_BUILDER_003"

    def __init__(self, message: str = "Project not found", **kwargs: object) -> None:
        super().__init__(message, **kwargs)


class GraphValidationError(BuilderError):
    """The graph document failed validation."""

    _code = "LEX_ERR_BUILDER_004"

    def __init__(
        self, message: str = "Graph validation failed", **kwargs: object
    ) -> None:
        super().__init__(message, **kwargs)


class PreviewError(BuilderError):
    """A preview lifecycle operation failed."""

    _code = "LEX_ERR_BUILDER_005"

    def __init__(self, message: str = "Preview error", **kwargs: object) -> None:
        super().__init__(message, **kwargs)

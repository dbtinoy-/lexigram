"""Exceptions for lexigram-ai-skills."""

from __future__ import annotations

from lexigram.contracts.ai.skills import SkillError


class SkillNotFoundError(SkillError):
    """Raised when a requested skill is not registered."""

    _code: str = "LEX_ERR_SKILL_002"

    def __init__(self, skill_name: str) -> None:
        """Initialise with the missing skill name.

        Args:
            skill_name: Name of the skill that was not found.
        """
        super().__init__(f"Skill not found: {skill_name!r}", skill_name=skill_name)
        self.skill_name = skill_name


class SkillAlreadyRegisteredError(SkillError):
    """Raised when a skill is registered under a name that already exists."""

    _code: str = "LEX_ERR_SKILL_003"

    def __init__(self, skill_name: str) -> None:
        """Initialise with the duplicate skill name.

        Args:
            skill_name: Name of the skill that was already registered.
        """
        super().__init__(
            f"Skill already registered: {skill_name!r}", skill_name=skill_name
        )


class SkillValidationError(SkillError):
    """Raised when skill parameter validation fails."""

    _code: str = "LEX_ERR_SKILL_004"

    def __init__(self, skill_name: str, errors: list[str]) -> None:
        """Initialise with validation error details.

        Args:
            skill_name: Name of the skill that failed validation.
            errors: List of human-readable validation error messages.
        """
        super().__init__(
            f"Validation failed for {skill_name!r}: {'; '.join(errors)}",
            skill_name=skill_name,
        )
        self.errors = errors


class SkillPermissionDeniedError(SkillError):
    """Raised when the caller lacks required permissions for a skill."""

    _code: str = "LEX_ERR_SKILL_005"

    def __init__(self, skill_name: str, required: list[str]) -> None:
        """Initialise with permission details.

        Args:
            skill_name: Name of the skill that requires permissions.
            required: Required permission strings.
        """
        super().__init__(
            f"Permission denied for {skill_name!r}. Required: {required}",
            skill_name=skill_name,
        )
        self.required = required


class SkillTimeoutError(SkillError):
    """Raised when skill execution exceeds the configured timeout."""

    _code: str = "LEX_ERR_SKILL_006"

    def __init__(self, skill_name: str, timeout_seconds: float) -> None:
        """Initialise with timeout context.

        Args:
            skill_name: Name of the skill that timed out.
            timeout_seconds: The timeout that was exceeded.
        """
        super().__init__(
            f"Skill {skill_name!r} timed out after {timeout_seconds}s",
            skill_name=skill_name,
        )
        self.skill_name = skill_name
        self.timeout_seconds = timeout_seconds


class SkillRoutingError(SkillError):
    """Raised when a SkillRouter finds no matching route."""

    _code: str = "LEX_ERR_SKILL_007"

    def __init__(self, message: str = "No matching route") -> None:
        """Initialise with an optional detail message.

        Args:
            message: Human-readable description of the routing failure.
        """
        super().__init__(message)


class SkillExecutionError(SkillError):
    """Raised when a skill execution fails after all retry attempts."""

    _code: str = "LEX_ERR_SKILL_008"

    def __init__(
        self,
        message: str,
        cause: Exception | None = None,
        skill_name: str | None = None,
    ) -> None:
        """Initialise with an error message and optional cause.

        Args:
            message: Human-readable error description.
            cause: The underlying exception, if any.
            skill_name: Name of the skill that failed (optional).
        """
        super().__init__(message, skill_name=skill_name)
        self.skill_name = skill_name
        self.cause = cause


__all__ = [
    "SkillAlreadyRegisteredError",
    "SkillExecutionError",
    "SkillNotFoundError",
    "SkillPermissionDeniedError",
    "SkillRoutingError",
    "SkillTimeoutError",
    "SkillValidationError",
]

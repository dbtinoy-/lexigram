"""Input sanitizer — blocks common prompt-injection patterns before rendering."""

from __future__ import annotations

import re

from lexigram.ai.prompt.exceptions import PromptValidationError

# Patterns that commonly appear in prompt-injection payloads.
# Each tuple is (name, compiled_pattern).
_INJECTION_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "ignore_instructions",
        re.compile(
            r"(?i)(ignore|disregard|forget|override)\s+(previous|prior|all|the)\s+"
            r"(instructions?|prompts?|context|rules?|constraints?)",
        ),
    ),
    (
        "role_override",
        re.compile(
            r"(?i)(you\s+are\s+now|act\s+as|pretend\s+to\s+be|your\s+new\s+role\s+is)",
        ),
    ),
    (
        "system_prompt_leak",
        re.compile(
            r"(?i)(print|show|reveal|output|display|repeat)\s+(your\s+)?"
            r"(system\s+prompt|instructions?|initial\s+prompt|prompt\s+above)",
        ),
    ),
    (
        "jinja2_expression",
        re.compile(r"\{\{.*?\}\}|\{%.*?%\}"),
    ),
]


class InputSanitizer:
    """Scans user-supplied variable values for prompt-injection attempts.

    Use :meth:`sanitize` to validate a single string or
    :meth:`sanitize_all` to check an entire variable mapping.

    Args:
        strict: When ``True`` (default), detected injections raise
                :class:`~lexigram.ai.prompt.exceptions.PromptValidationError`.
                When ``False``, the violating string is returned as-is and a
                warning is recorded in :attr:`warnings`.
        extra_patterns: Additional compiled patterns to check.
    """

    def __init__(
        self,
        strict: bool = True,
        extra_patterns: list[re.Pattern[str]] | None = None,
    ) -> None:
        self._strict = strict
        self._extra: list[re.Pattern[str]] = extra_patterns or []
        self.warnings: list[str] = []

    def sanitize(self, value: str, variable_name: str = "input") -> str:
        """Check *value* for injection patterns.

        Args:
            value: String to inspect.
            variable_name: Name used in error messages.

        Returns:
            The (unchanged) *value* when no injection is detected.

        Raises:
            :class:`~lexigram.ai.prompt.exceptions.PromptValidationError`:
                Detection in strict mode.
        """
        for name, pattern in _INJECTION_PATTERNS:
            if pattern.search(value):
                msg = (
                    f"Potential prompt injection detected in '{variable_name}' "
                    f"(pattern: '{name}')."
                )
                if self._strict:
                    raise PromptValidationError(msg)
                self.warnings.append(msg)
                return value

        for pattern in self._extra:
            if pattern.search(value):
                msg = f"Custom injection pattern matched in '{variable_name}'."
                if self._strict:
                    raise PromptValidationError(msg)
                self.warnings.append(msg)

        return value

    def sanitize_all(self, variables: dict[str, object]) -> dict[str, object]:
        """Check all string values in *variables*.

        Non-string values are passed through unchanged.

        Args:
            variables: Variable name → value mapping.

        Returns:
            The same mapping (values are not mutated).
        """
        for key, value in variables.items():
            if isinstance(value, str):
                self.sanitize(value, variable_name=key)
        return variables


__all__ = ["InputSanitizer"]

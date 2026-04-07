"""Variable validators — ensure provided values satisfy their ``PromptVariable`` spec."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.ai.prompt.exceptions import PromptValidationError

if TYPE_CHECKING:
    from lexigram.ai.prompt.variables.types import PromptVariable


def validate_variable(var: PromptVariable, value: Any) -> None:
    """Validate *value* against *var*'s constraints.

    Raises:
        :class:`~lexigram.ai.prompt.exceptions.PromptValidationError` when
        a constraint is violated.
    """
    # --- type check ---
    if not isinstance(value, var.type):
        raise PromptValidationError(
            f"Variable '{var.name}': expected {var.type.__name__}, "
            f"got {type(value).__name__}."
        )

    # --- max_length ---
    if var.max_length is not None:
        str_value = str(value) if not isinstance(value, str) else value
        if len(str_value) > var.max_length:
            raise PromptValidationError(
                f"Variable '{var.name}': value length {len(str_value)} "
                f"exceeds max_length={var.max_length}."
            )

    # --- allowed_values ---
    if var.allowed_values is not None and value not in var.allowed_values:
        raise PromptValidationError(
            f"Variable '{var.name}': value {value!r} is not in allowed_values "
            f"{var.allowed_values!r}."
        )


def resolve_variables(
    declared: list[PromptVariable],
    supplied: dict[str, Any],
) -> dict[str, Any]:
    """Resolve and validate all *supplied* values against *declared* variables.

    Missing required variables raise
    :class:`~lexigram.ai.prompt.exceptions.PromptRenderError`.  Missing
    optional variables fall back to their ``default``.

    Args:
        declared: List of :class:`~lexigram.ai.prompt.variables.types.PromptVariable`
                  objects that describe accepted variables.
        supplied: Mapping of variable name → caller-provided value.

    Returns:
        Fully resolved ``{name: value}`` mapping ready for template substitution.

    Raises:
        :class:`~lexigram.ai.prompt.exceptions.PromptRenderError`:
            A required variable is absent.
        :class:`~lexigram.ai.prompt.exceptions.PromptValidationError`:
            A value fails type/length/allowed constraint.
    """
    from lexigram.ai.prompt.exceptions import PromptRenderError

    resolved: dict[str, Any] = {}
    declared_names = {v.name for v in declared}

    for var in declared:
        if var.name in supplied:
            value = supplied[var.name]
            validate_variable(var, value)
            resolved[var.name] = value
        elif var.required:
            raise PromptRenderError(f"Required variable '{var.name}' was not supplied.")
        else:
            resolved[var.name] = var.default

    # Pass through any extra kwargs that aren't declared (permissive mode).
    resolved.update(
        {key: value for key, value in supplied.items() if key not in declared_names}
    )

    return resolved


__all__ = ["resolve_variables", "validate_variable"]

"""BaseSkill, FunctionSkill, and ToolSkillAdapter — skill building blocks."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, cast

from lexigram.contracts.ai.skills import (
    SkillDefinition,
    SkillError,
    SkillResult,
)

if TYPE_CHECKING:
    from collections.abc import Awaitable, Callable

    from lexigram.contracts.ai.agents import ToolProtocol
from lexigram.result import Err, Ok, Result


class AbstractSkill(ABC):
    """Abstract base class for class-based skill definitions.

    Subclass this and define a ``definition`` class attribute plus an
    ``execute`` method.  Parameter validation default uses the JSON schema
    stored on the definition; override ``validate`` for custom rules.
    """

    definition: SkillDefinition

    @abstractmethod
    async def execute(self, **kwargs: Any) -> Result[SkillResult, SkillError]:
        """Execute the skill with the provided keyword arguments.

        Args:
            **kwargs: Skill parameters as keyword arguments.

        Returns:
            Result wrapping SkillResult on success or SkillError on failure.
        """

    def validate(self, params: dict[str, Any]) -> list[str]:
        """Validate *params* against the skill definition's parameter schema.

        Args:
            params: Parameters to validate.

        Returns:
            List of validation error messages (empty list means valid).
        """
        from lexigram.ai.skills.validation.schema import validate_params

        return validate_params(params, self.definition.parameters_schema)

    def to_tool(self) -> SkillToolAdapter:
        """Convert this skill to a ToolProtocol for use in Lexigram agents.

        Returns:
            A SkillToolAdapter that implements ToolProtocol.
        """
        return SkillToolAdapter(self)


class FunctionSkill:
    """Wraps an async function decorated with ``@skill`` as a SkillProtocol.

    Created automatically by the ``@skill`` decorator — not intended for
    direct instantiation.
    """

    def __init__(
        self,
        fn: Callable[..., Awaitable[Any]],
        definition: SkillDefinition,
        param_names: list[str] | None = None,
    ) -> None:
        """Initialise a FunctionSkill.

        Args:
            fn: The underlying async callable.
            definition: The skill's definition metadata.
            param_names: Ordered list of declared parameter names from
                ``@skill_param`` decorators (used for schema building).
        """
        self._fn = fn
        self._definition = definition
        self._param_names = param_names or []

    @property
    def definition(self) -> SkillDefinition:
        """Return the skill definition.

        Returns:
            The SkillDefinition for this function skill.
        """
        return self._definition

    async def execute(self, **kwargs: Any) -> Result[SkillResult, SkillError]:
        """Call the wrapped async function and wrap its return value.

        Args:
            **kwargs: Parameters forwarded to the underlying function.

        Returns:
            Result wrapping SkillResult on success or SkillError on failure.
        """
        try:
            output = await self._fn(**kwargs)
            if (
                isinstance(output, dict)
                and "skill_name" in output
                and "success" in output
            ):
                # Already a SkillResult-like dict — shouldn't happen but handle gracefully
                return Ok(
                    SkillResult(
                        skill_name=self._definition.name,
                        success=output.get("success", True),
                        output=output,
                    )
                )
            return Ok(
                SkillResult(
                    skill_name=self._definition.name,
                    success=True,
                    output=output,
                )
            )
        except SkillError as exc:
            return Err(exc)
        except Exception as exc:  # noqa: BLE001
            return Err(
                SkillError(
                    f"Unexpected error in {self._definition.name!r}: {exc}",
                    skill_name=self._definition.name,
                )
            )

    def validate(self, params: dict[str, Any]) -> list[str]:
        """Validate *params* against the JSON schema in the definition.

        Args:
            params: Parameters to validate.

        Returns:
            List of validation error messages.
        """
        from lexigram.ai.skills.validation.schema import validate_params

        return validate_params(params, self._definition.parameters_schema)

    def to_tool(self) -> SkillToolAdapter:
        """Convert this skill to a ToolProtocol for use in Lexigram agents.

        Returns:
            A SkillToolAdapter that implements ToolProtocol.
        """
        return SkillToolAdapter(cast("AbstractSkill", self))


class ToolSkillAdapter:
    """Adapts a ``ToolProtocol`` into a ``SkillProtocol``.

    Allows existing tool-based registries to participate in the skill
    system without modification.
    """

    def __init__(self, tool: ToolProtocol) -> None:
        """Wrap *tool* as a skill.

        Args:
            tool: ToolProtocol-compliant object with name, description,
                parameters_schema, and execute() method.
        """
        self._tool = tool
        self._definition = SkillDefinition(
            name=getattr(tool, "name", str(tool)),
            description=getattr(tool, "description", ""),
            parameters_schema=getattr(tool, "parameters_schema", {}),
            category="tool",
        )

    @property
    def definition(self) -> SkillDefinition:
        """Return the adapted skill definition.

        Returns:
            SkillDefinition derived from the wrapped tool.
        """
        return self._definition

    async def execute(self, **kwargs: Any) -> Result[SkillResult, SkillError]:
        """Delegate to the wrapped tool's execute method.

        Args:
            **kwargs: Parameters forwarded to the tool.

        Returns:
            Result wrapping SkillResult on success or SkillError on failure.
        """
        try:
            output = await self._tool.execute(**kwargs)
            return Ok(
                SkillResult(
                    skill_name=self._definition.name,
                    success=True,
                    output=output,
                )
            )
        except SkillError as exc:
            return Err(exc)
        except Exception as exc:  # noqa: BLE001
            return Err(
                SkillError(
                    f"Tool {self._definition.name!r} raised: {exc}",
                    skill_name=self._definition.name,
                )
            )

    def validate(self, params: dict[str, Any]) -> list[str]:
        """Tools have no built-in validation — always returns empty list.

        Args:
            params: Ignored.

        Returns:
            Empty list.
        """
        return []


class SkillToolAdapter:
    """Adapts a ``SkillProtocol`` into a ``ToolProtocol``.

    Allows skills to be registered directly into an agent's ToolRegistry.
    """

    def __init__(self, skill: AbstractSkill) -> None:
        """Wrap *skill* as a tool.

        Args:
            skill: Any object satisfying SkillProtocol.
        """
        self._skill = skill

    @property
    def name(self) -> str:
        """Unique tool identifier."""
        return self._skill.definition.name

    @property
    def description(self) -> str:
        """Human-readable description for the LLM."""
        return self._skill.definition.description

    @property
    def parameters_schema(self) -> dict[str, Any]:
        """JSON Schema describing the tool's parameters."""
        return self._skill.definition.parameters_schema

    async def execute(self, **kwargs: Any) -> Any:
        """Delegate to the wrapped skill execute method.

        Args:
            **kwargs: Parameters forwarded to the skill.

        Returns:
            The raw skill output on success.

        Raises:
            Exception: If the skill returns an Err.
        """
        result = await self._skill.execute(**kwargs)
        if result.is_err():
            err = result.unwrap_err()
            raise err
        return result.unwrap().output


__all__ = ["AbstractSkill", "FunctionSkill", "SkillToolAdapter", "ToolSkillAdapter"]

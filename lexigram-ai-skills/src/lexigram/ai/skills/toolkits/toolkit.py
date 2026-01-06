"""Base Toolkit class and related functionality."""

from __future__ import annotations

from lexigram.contracts.ai.skills import (
    SkillProtocol,
    ToolkitProtocol,
)


class Toolkit(ToolkitProtocol):
    """Base class for skill toolkits.

    A toolkit is a collection of related skills that can be used together.
    Subclass this to create a custom toolkit.
    """

    def __init__(self, name: str, description: str) -> None:
        """Initialise the toolkit.

        Args:
            name: Unique identifier for this toolkit.
            description: Human-readable description of what this toolkit provides.
        """
        self._name = name
        self._description = description

    @property
    def tools(self) -> tuple[SkillProtocol, ...]:
        """Get the collection of skills in this toolkit.

        Returns:
            Tuple of SkillProtocol instances provided by this toolkit.
        """
        return self._get_tools()

    @property
    def name(self) -> str:
        """Get the toolkit name.

        Returns:
            Unique identifier for this toolkit.
        """
        return self._name

    @property
    def description(self) -> str:
        """Get the toolkit description.

        Returns:
            Human-readable description of what this toolkit provides.
        """
        return self._description

    def _get_tools(self) -> tuple[SkillProtocol, ...]:
        """Subclasses override to provide their skills.

        Returns:
            Tuple of SkillProtocol instances.
        """
        return ()


__all__ = ["Toolkit"]

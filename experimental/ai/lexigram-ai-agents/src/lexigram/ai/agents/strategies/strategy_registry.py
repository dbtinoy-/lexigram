"""Agent reasoning strategy registry.

Maps strategy names (``"react"``, ``"reflexion"``, ``"plan-execute"``)
to strategy *classes* and instantiates on demand via
:meth:`~lexigram.primitives.registry.StrategyRegistry.instantiate`.
"""

from __future__ import annotations

from lexigram.logging import (
    get_logger,
)
from lexigram.primitives.registry import StrategyRegistry

logger = get_logger(__name__)


class AgentStrategyRegistry(StrategyRegistry):
    """Registry of agent reasoning strategy implementations.

    Usage::

        registry = AgentStrategyRegistry.with_defaults()
        strategy = registry.instantiate("react", max_iterations=10)
    """

    def __init__(self) -> None:
        super().__init__(name="agent.strategies", allow_overwrite=True)

    # ------------------------------------------------------------------
    # Factory
    # ------------------------------------------------------------------

    @classmethod
    def with_defaults(cls) -> AgentStrategyRegistry:
        """Create a registry pre-populated with the built-in strategies.

        Returns:
            A new registry with ``react``, ``plan-execute``, and
            ``reflexion`` strategies registered.
        """
        instance = cls()
        instance._register_defaults()
        return instance

    def _register_defaults(self) -> None:
        """Populate the registry with built-in strategy classes."""
        from lexigram.ai.agents.strategies.function_calling import (
            FunctionCallingStrategy,
        )
        from lexigram.ai.agents.strategies.plan_execute import PlanAndExecuteStrategy
        from lexigram.ai.agents.strategies.react import ReActStrategy
        from lexigram.ai.agents.strategies.reflexion import ReflexionStrategy

        self.register("react", ReActStrategy)
        self.register("function_calling", FunctionCallingStrategy)
        self.register("plan-execute", PlanAndExecuteStrategy)
        self.register("reflexion", ReflexionStrategy)

    # ------------------------------------------------------------------
    # Overrides
    # ------------------------------------------------------------------

    def default_strategies(self) -> dict[str, type]:
        """Return built-in strategy key → class mapping.

        Returns:
            Dict mapping strategy name to its class.
        """
        from lexigram.ai.agents.strategies.function_calling import (
            FunctionCallingStrategy,
        )
        from lexigram.ai.agents.strategies.plan_execute import PlanAndExecuteStrategy
        from lexigram.ai.agents.strategies.react import ReActStrategy
        from lexigram.ai.agents.strategies.reflexion import ReflexionStrategy

        return {
            "react": ReActStrategy,
            "function_calling": FunctionCallingStrategy,
            "plan-execute": PlanAndExecuteStrategy,
            "reflexion": ReflexionStrategy,
        }

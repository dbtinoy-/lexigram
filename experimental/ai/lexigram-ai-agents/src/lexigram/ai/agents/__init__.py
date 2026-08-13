"""lexigram-ai-agents — Agent system for Lexigram Framework.

Canonical import paths
-----------------------
AgentBase class:     from lexigram.ai.agents import AgentBase
Tool decorator:      from lexigram.ai.agents import tool
Tool registry:       from lexigram.ai.agents import ToolRegistryImpl
Agent executor:      from lexigram.ai.agents import AgentExecutorImpl
ReAct strategy:      from lexigram.ai.agents import ReActStrategy
Crew:                from lexigram.ai.agents import Crew
CrewTask:            from lexigram.ai.agents import CrewTask
CrewBuilder:         from lexigram.ai.agents import CrewBuilder
Process:             from lexigram.ai.agents import Process

Quick Start
-----------

    from lexigram.ai.agents import AgentBase, tool

    @tool
    async def lookup_order(order_id: str) -> dict:
        \"\"\"Look up an order by its ID.\"\"\"
        return {"order_id": order_id, "status": "shipped"}

    class OrderAgent(AgentBase):
        name = "order_agent"
        system_prompt = "You are a helpful order support agent."

        @property
        def tools(self):
            return [lookup_order]
"""

from __future__ import annotations

import importlib.metadata
import pkgutil
from typing import TYPE_CHECKING, Any

__path__ = pkgutil.extend_path(__path__, __name__)

from lexigram.ai.agents.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.ai.agents.agent import AgentBase, AgentBuilder
    from lexigram.ai.agents.config import AgentConfig
    from lexigram.ai.agents.crew import (
        Crew,
        CrewBuilder,
        CrewExecutionResult,
        CrewRunner,
        CrewTask,
        Process,
        TaskResult,
    )
    from lexigram.ai.agents.decorators import strategy
    from lexigram.ai.agents.delegation import AgentAsToolAdapter
    from lexigram.ai.agents.di.provider import AgentsProvider
    from lexigram.ai.agents.events import (
        AgentRunCompletedEvent,
        ToolExecutionCompletedEvent,
    )
    from lexigram.ai.agents.exceptions import (
        AgentConfigurationError,
        AgentError,
        AgentExecutionError,
        BudgetExceededError,
        MaxIterationsExceededError,
        StrategyError,
        ToolAccessDeniedError,
        ToolError,
        ToolExecutionError,
        ToolNotFoundError,
    )
    from lexigram.ai.agents.executor import AgentExecutorImpl
    from lexigram.ai.agents.hooks import (
        AgentCompletedHook,
        AgentStartedHook,
        AgentToolCalledHook,
    )
    from lexigram.ai.agents.module import AgentsModule
    from lexigram.ai.agents.protocols import ObserverProtocol, PlannerProtocol
    from lexigram.ai.agents.strategies import (
        AbstractStrategy,
        PlanAndExecuteStrategy,
        PlanStepStatus,
        ReActStrategy,
        ReflexionStrategy,
        SupervisorStrategy,
    )
    from lexigram.ai.agents.strategies.strategy_registry import AgentStrategyRegistry
    from lexigram.ai.agents.tools import AbstractTool, ToolRegistryImpl, tool
    from lexigram.ai.agents.types import (
        AgentResponse,
        ReasoningStep,
        ToolExecutionRecord,
    )

_LAZY_IMPORTS: dict[str, str] = {
    # Events
    "AgentRunCompletedEvent": "lexigram.ai.agents.events",
    # Hooks
    "AgentCompletedHook": "lexigram.ai.agents.hooks",
    "AgentStartedHook": "lexigram.ai.agents.hooks",
    "AgentToolCalledHook": "lexigram.ai.agents.hooks",
    "AbstractStrategy": "lexigram.ai.agents.strategies",
    "AbstractTool": "lexigram.ai.agents.tools",
    "AgentAsToolAdapter": "lexigram.ai.agents.delegation",
    "AgentBase": "lexigram.ai.agents.agent",
    "AgentBuilder": "lexigram.ai.agents.agent",
    "AgentConfig": "lexigram.ai.agents.config",
    "AgentStrategyRegistry": "lexigram.ai.agents.strategies.strategy_registry",
    "Crew": "lexigram.ai.agents.crew",
    "CrewBuilder": "lexigram.ai.agents.crew",
    "CrewExecutionResult": "lexigram.ai.agents.crew",
    "CrewRunner": "lexigram.ai.agents.crew",
    "CrewTask": "lexigram.ai.agents.crew",
    "Process": "lexigram.ai.agents.crew",
    "TaskResult": "lexigram.ai.agents.crew",
    "AgentConfigurationError": "lexigram.ai.agents.exceptions",
    "AgentError": "lexigram.ai.agents.exceptions",
    "AgentExecutionError": "lexigram.ai.agents.exceptions",
    "AgentExecutorImpl": "lexigram.ai.agents.executor",
    "AgentResponse": "lexigram.ai.agents.types",
    "AgentsModule": "lexigram.ai.agents.module",
    "AgentsProvider": "lexigram.ai.agents.di.provider",
    "BudgetExceededError": "lexigram.ai.agents.exceptions",
    "MaxIterationsExceededError": "lexigram.ai.agents.exceptions",
    "PlanAndExecuteStrategy": "lexigram.ai.agents.strategies",
    "PlanStepStatus": "lexigram.ai.agents.strategies",
    "ReActStrategy": "lexigram.ai.agents.strategies",
    "ReflexionStrategy": "lexigram.ai.agents.strategies",
    "SupervisorStrategy": "lexigram.ai.agents.strategies",
    "ReasoningStep": "lexigram.ai.agents.types",
    "strategy": "lexigram.ai.agents.decorators",
    "StrategyError": "lexigram.ai.agents.exceptions",
    "ToolAccessDeniedError": "lexigram.ai.agents.exceptions",
    "ToolExecutionCompletedEvent": "lexigram.ai.agents.events",
    "ToolExecutionRecord": "lexigram.ai.agents.types",
    "ToolError": "lexigram.ai.agents.exceptions",
    "ToolExecutionError": "lexigram.ai.agents.exceptions",
    "ToolNotFoundError": "lexigram.ai.agents.exceptions",
    "ToolRegistryImpl": "lexigram.ai.agents.tools",
    "tool": "lexigram.ai.agents.tools",
    # Internal protocols
    "PlannerProtocol": "lexigram.ai.agents.protocols",
    "ObserverProtocol": "lexigram.ai.agents.protocols",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib as _importlib

        module = _importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = [
    "AbstractStrategy",
    "AbstractTool",
    "AgentAsToolAdapter",
    "AgentBase",
    "AgentBuilder",
    "AgentCompletedHook",
    "AgentConfig",
    "AgentConfigurationError",
    "AgentError",
    "AgentExecutionError",
    "AgentExecutorImpl",
    "AgentResponse",
    "AgentRunCompletedEvent",
    "AgentStartedHook",
    "AgentStrategyRegistry",
    "AgentToolCalledHook",
    "AgentsModule",
    "AgentsProvider",
    "BudgetExceededError",
    "Crew",
    "CrewBuilder",
    "CrewExecutionResult",
    "CrewRunner",
    "CrewTask",
    "MaxIterationsExceededError",
    "ObserverProtocol",
    "PlanAndExecuteStrategy",
    "PlanStepStatus",
    "PlannerProtocol",
    "Process",
    "ReActStrategy",
    "ReasoningStep",
    "ReflexionStrategy",
    "StrategyError",
    "SupervisorStrategy",
    "TaskResult",
    "ToolAccessDeniedError",
    "ToolError",
    "ToolExecutionCompletedEvent",
    "ToolExecutionError",
    "ToolExecutionRecord",
    "ToolNotFoundError",
    "ToolRegistryImpl",
    "strategy",
    "tool",
]

"""Agent contracts for the Lexigram framework.

Exceptions, types, and protocols for agents, tools, and strategies.
"""

from __future__ import annotations

from lexigram.contracts.ai.agents.exceptions import AgentError as AgentError
from lexigram.contracts.ai.agents.exceptions import StrategyError as StrategyError
from lexigram.contracts.ai.agents.exceptions import ToolError as ToolError
from lexigram.contracts.ai.agents.protocols import (
    AgentExecutorProtocol as AgentExecutorProtocol,
)
from lexigram.contracts.ai.agents.protocols import AgentProtocol as AgentProtocol
from lexigram.contracts.ai.agents.protocols import (
    AgentStrategyProtocol as AgentStrategyProtocol,
)
from lexigram.contracts.ai.agents.protocols import MemoryProtocol as MemoryProtocol
from lexigram.contracts.ai.agents.protocols import (
    RunnableAgentProtocol as RunnableAgentProtocol,
)
from lexigram.contracts.ai.agents.protocols import (
    SkillComposerProtocol as SkillComposerProtocol,
)
from lexigram.contracts.ai.agents.protocols import StrategyProtocol as StrategyProtocol
from lexigram.contracts.ai.agents.protocols import ToolProtocol as ToolProtocol
from lexigram.contracts.ai.agents.protocols import (
    ToolRegistryProtocol as ToolRegistryProtocol,
)
from lexigram.contracts.ai.agents.types import AgentEvent as AgentEvent
from lexigram.contracts.ai.agents.types import AgentEventType as AgentEventType
from lexigram.contracts.ai.agents.types import (
    AgentExecutionContext as AgentExecutionContext,
)
from lexigram.contracts.ai.agents.types import AgentResponse as AgentResponse
from lexigram.contracts.ai.agents.types import ToolDefinition as ToolDefinition
from lexigram.contracts.ai.agents.types import ToolResult as ToolResult

__all__ = [
    "AgentError",
    "AgentEvent",
    "AgentEventType",
    "AgentExecutionContext",
    "AgentExecutorProtocol",
    "AgentProtocol",
    "AgentResponse",
    "AgentStrategyProtocol",
    "MemoryProtocol",
    "RunnableAgentProtocol",
    "SkillComposerProtocol",
    "StrategyError",
    "StrategyProtocol",
    "ToolDefinition",
    "ToolError",
    "ToolProtocol",
    "ToolRegistryProtocol",
    "ToolResult",
]

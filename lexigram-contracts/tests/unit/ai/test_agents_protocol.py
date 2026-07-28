"""Tests for Agent contracts (G-05 parity)."""
from __future__ import annotations


def test_agent_executor_basic():
    """AgentExecutor should execute an agent."""
    from lexigram.contracts.ai.agents import AgentExecutor
    
    class MockAgent:
        async def plan(self, input: str) -> str:
            return f"planned: {input}"
        
        async def execute(self, plan: str) -> str:
            return f"executed: {plan}"
    
    executor = AgentExecutor(MockAgent())
    result = executor.run("hello")
    assert "hello" in result


def test_agent_with_tools():
    """Agent with tools should be able to use them."""
    from lexigram.contracts.ai.agents import AgentWithTools
    from lexigram.contracts.ai.tools import Tool
    
    class MockTool(Tool):
        def __init__(self):
            super().__init__(name="search", description="Search")
        
        def invoke(self, *args, **kwargs):
            return "search results"
    
    agent = AgentWithTools(tools=[MockTool()])
    assert len(agent.tools) == 1


def test_plan_execute_agent():
    """PlanExecuteAgent should plan then execute."""
    from lexigram.contracts.ai.agents import PlanExecuteAgent
    
    agent = PlanExecuteAgent()
    result = agent.run("test input")
    assert result is not None

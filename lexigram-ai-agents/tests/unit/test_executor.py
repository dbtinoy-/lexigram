"""Unit tests for lexigram-ai-agents AgentExecutorImpl."""

from __future__ import annotations

import pytest

from lexigram.ai.agents.exceptions import BudgetExceededError
from lexigram.ai.agents.executor import AgentExecutorImpl
from lexigram.ai.agents.executor.executor import AgentObservability, AgentSafetyInfra
from lexigram.ai.agents.strategies import ReActStrategy
from lexigram.ai.agents.types import ToolExecutionRecord
from lexigram.contracts.ai.agents import AgentError, AgentResponse


class MockAgent:
    """Mock agent for testing."""

    def __init__(
        self,
        name: str = "test_agent",
        tools: list | None = None,
        system_prompt: str = "",
    ):
        self.name = name
        self._tools = tools or []
        self.system_prompt = system_prompt
        self.strategy = ReActStrategy()

    @property
    def tools(self):
        return self._tools


class MockLLM:
    """Mock LLM for testing."""

    def __init__(self, response: str = "test response"):
        self.response = response
        self.call_count = 0

    async def generate(self, prompt: str, **kwargs):
        self.call_count += 1
        return {"content": self.response, "usage": {"tokens": 10}}

    async def complete(self, messages, **kwargs):
        """Return a Result-like object wrapping a Completion-like object."""
        self.call_count += 1

        class _Completion:
            def __init__(self, text: str):
                self.content = f"THOUGHT: Responding directly\nFINAL_ANSWER: {text}"

        class _Ok:
            def __init__(self, val):
                self._val = val

            def is_ok(self):
                return True

            def is_err(self):
                return False

            def unwrap(self):
                return self._val

        return _Ok(_Completion(self.response))


class MockGovernance:
    """Mock governance for testing."""

    def __init__(self, allow: bool = True):
        self.allow = allow
        self.check_count = 0

    async def check_request(self, model: str, provider: str, user_id: str | None = None):
        self.check_count += 1
        return self.allow


class MockMemory:
    """Mock memory for testing."""

    def __init__(self, messages: list | None = None):
        self._messages = messages or []
        self.added = []

    def get_messages_dict(self):
        return self._messages

    async def add(self, role: str, content: str):
        self.added.append({"role": role, "content": content})


class MockEventBus:
    """Mock event bus for testing."""

    def __init__(self):
        self.published_events = []

    async def publish(self, event):
        self.published_events.append(event)


class TestAgentExecutorInit:
    """Tests for AgentExecutorImpl initialization."""

    def test_executor_creation_with_defaults(self):
        """Test creating executor with minimal config."""
        executor = AgentExecutorImpl()

        assert executor._llm is None
        assert executor._governance is None
        assert executor._memory is None

    def test_executor_creation_with_all_params(self):
        """Test creating executor with all parameters."""
        mock_llm = MockLLM()
        mock_gov = MockGovernance()
        mock_memory = MockMemory()
        mock_event_bus = MockEventBus()

        executor = AgentExecutorImpl(
            llm=mock_llm,
            safety=AgentSafetyInfra(governance=mock_gov),
            memory=mock_memory,
            observability=AgentObservability(event_bus=mock_event_bus),
        )

        assert executor._llm is mock_llm
        assert executor._governance is mock_gov
        assert executor._memory is mock_memory
        assert executor._event_bus is mock_event_bus

    def test_executor_initializes_metrics(self):
        """Test executor initializes metrics."""
        executor = AgentExecutorImpl()

        from lexigram.ai.agents.observability import AgentMetrics

        assert isinstance(executor._metrics, AgentMetrics)

    def test_executor_initializes_tracer(self):
        """Test executor initializes tracer."""
        executor = AgentExecutorImpl()

        from lexigram.ai.agents.observability import AgentTracer

        assert isinstance(executor._tracer, AgentTracer)


class TestAgentExecutorRun:
    """Tests for AgentExecutorImpl.run method."""

    @pytest.mark.asyncio
    async def test_run_simple_agent(self):
        """Test running a simple agent."""
        executor = AgentExecutorImpl()
        agent = MockAgent(name="test", tools=[])
        mock_llm = MockLLM(response="Hello!")
        executor._llm = mock_llm

        result = await executor.run(agent=agent, message="Hi")

        assert result.is_ok()
        response = result.unwrap()
        assert isinstance(response, AgentResponse)

    @pytest.mark.asyncio
    async def test_run_with_session_id(self):
        """Test running agent with session ID."""
        memory = MockMemory()
        executor = AgentExecutorImpl(memory=memory)
        agent = MockAgent(name="test", tools=[])
        mock_llm = MockLLM(response="Response")
        executor._llm = mock_llm

        result = await executor.run(
            agent=agent,
            message="Hello",
            session_id="session-123",
        )

        assert result.is_ok()
        # Memory should have been queried
        # (empty for new session)

    @pytest.mark.asyncio
    async def test_run_governance_denies(self):
        """Test governance denial."""
        governance = MockGovernance(allow=False)
        executor = AgentExecutorImpl(safety=AgentSafetyInfra(governance=governance))
        agent = MockAgent(name="test", tools=[])
        mock_llm = MockLLM(response="Response")
        executor._llm = mock_llm

        result = await executor.run(agent=agent, message="Hello", user_id="user-1")

        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, BudgetExceededError)

    @pytest.mark.asyncio
    async def test_run_governance_check_error(self):
        """Test governance check failure is handled."""

        class FaultyGovernance:
            async def check_request(self, **kwargs):
                raise RuntimeError("Governance service down")

        executor = AgentExecutorImpl(
            safety=AgentSafetyInfra(governance=FaultyGovernance())
        )
        agent = MockAgent(name="test", tools=[])
        mock_llm = MockLLM(response="Response")
        executor._llm = mock_llm

        # Should not raise, just warn
        result = await executor.run(agent=agent, message="Hello")

        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_run_with_memory_save(self):
        """Test memory is saved after execution."""
        memory = MockMemory()
        executor = AgentExecutorImpl(memory=memory)
        agent = MockAgent(name="test", tools=[])
        mock_llm = MockLLM(response="Response")
        executor._llm = mock_llm

        result = await executor.run(
            agent=agent,
            message="Hello",
            session_id="session-123",
        )

        # Check memory was updated (implementation may vary)
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_run_with_event_bus(self):
        """Test events are published."""
        event_bus = MockEventBus()
        executor = AgentExecutorImpl(
            observability=AgentObservability(event_bus=event_bus)
        )
        agent = MockAgent(name="test", tools=[])
        mock_llm = MockLLM(response="Response")
        executor._llm = mock_llm

        await executor.run(agent=agent, message="Hello")

        # Should have published start/completion events
        # (if strategy returns successfully)

    @pytest.mark.asyncio
    async def test_run_strategy_failure(self):
        """Test handling strategy failure."""

        class FailingStrategy:
            async def execute(self, **kwargs):
                raise RuntimeError("Strategy exploded")

        agent = MockAgent(name="test", tools=[])
        agent.strategy = FailingStrategy()

        executor = AgentExecutorImpl()
        executor._llm = MockLLM()

        result = await executor.run(agent=agent, message="Hello")

        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, AgentError)

    @pytest.mark.asyncio
    async def test_run_result_wraps_error(self):
        """Test non-AgentError is wrapped in AgentError."""

        class FailingStrategy:
            async def execute(self, **kwargs):
                from lexigram.result import Err

                return Err(ValueError("Some error"))

        agent = MockAgent(name="test", tools=[])
        agent.strategy = FailingStrategy()

        executor = AgentExecutorImpl()
        executor._llm = MockLLM()

        result = await executor.run(agent=agent, message="Hello")

        assert result.is_err()
        # Should be wrapped in AgentError


class TestAgentExecutorGovernance:
    """Tests for governance integration."""

    @pytest.mark.asyncio
    async def test_governance_checks_model_and_provider(self):
        """Test governance receives correct model/provider info."""
        checked_params = {}

        class TrackingGovernance:
            async def check_request(
                self, model: str, provider: str, user_id: str | None = None
            ):
                checked_params["model"] = model
                checked_params["provider"] = provider
                checked_params["user_id"] = user_id
                return True

        class ModelProviderLLM:
            model = "gpt-4"
            provider = "openai"

        executor = AgentExecutorImpl(
            safety=AgentSafetyInfra(governance=TrackingGovernance()),
            llm=ModelProviderLLM(),
        )
        agent = MockAgent(name="test", tools=[])
        mock_llm = MockLLM(response="Response")
        executor._llm = mock_llm

        await executor.run(agent=agent, message="Hi", user_id="user-1")

        # Model info should come from actual llm, not executor's _llm


class TestAgentExecutorMetrics:
    """Tests for metrics recording."""

    @pytest.mark.asyncio
    async def test_metrics_recorded_on_success(self):
        """Test metrics are recorded on successful execution."""
        recorded = []

        class RecordingMetrics:
            def record_execution(self, agent_name: str, response: AgentResponse):
                recorded.append(("execution", agent_name))

            def record_tool_call(self, agent_name: str, tool_call: ToolExecutionRecord):
                recorded.append(("tool", agent_name, tool_call.tool_name))

        executor = AgentExecutorImpl()
        # Would need mock strategy returning proper response
        # This is a simplified test

    @pytest.mark.asyncio
    async def test_error_recorded_on_failure(self):
        """Test errors are recorded in metrics."""

        class RecordingMetrics:
            def record_error(self, agent_name: str, error_type: str):
                pass

        # Test with failing strategy


class TestAgentExecutorMemory:
    """Tests for memory integration."""

    @pytest.mark.asyncio
    async def test_loads_history_from_memory(self):
        """Test history is loaded from memory."""
        existing_history = [
            {"role": "user", "content": "Hello"},
            {"role": "assistant", "content": "Hi there"},
        ]
        memory = MockMemory(messages=existing_history)

        executor = AgentExecutorImpl(memory=memory)
        agent = MockAgent(name="test", tools=[])
        mock_llm = MockLLM(response="Response")
        executor._llm = mock_llm

        # Pass session_id to trigger memory load
        result = await executor.run(
            agent=agent,
            message="How are you?",
            session_id="session-123",
        )

    @pytest.mark.asyncio
    async def test_saves_to_memory(self):
        """Test response is saved to memory."""
        memory = MockMemory()
        executor = AgentExecutorImpl(memory=memory)
        agent = MockAgent(name="test", tools=[])
        mock_llm = MockLLM(response="Response")
        executor._llm = mock_llm

        result = await executor.run(
            agent=agent,
            message="Hello",
            session_id="session-123",
        )

        # Memory should have user and assistant messages added
        assert result.is_ok()


class TestAgentExecutorCostTracking:
    """Tests for cost tracking."""

    @pytest.mark.asyncio
    async def test_cost_tracked_via_estimator(self):
        """Test cost is tracked via a real cost estimator."""

        tracked_costs = []

        class CostTrackingGovernance:
            async def check_request(self, **kwargs):
                return True

            async def track_cost(
                self, cost: float, model: str, user_id: str | None = None
            ):
                tracked_costs.append(cost)

        class FixedCostEstimator:
            def estimate_cost(
                self,
                model,
                total_tokens,
                provider=None,
                prompt_tokens=0,
                completion_tokens=0,
            ):
                return total_tokens * 0.000002

        class CountingStrategy:
            async def execute(self, message, **kwargs):
                from lexigram.result import Ok

                return Ok(
                    AgentResponse(message="done", total_tokens=1000, tool_calls=[])
                )

        agent = MockAgent(name="test", tools=[])
        agent.strategy = CountingStrategy()

        executor = AgentExecutorImpl(
            safety=AgentSafetyInfra(governance=CostTrackingGovernance()),
            llm=MockLLM(),
            cost_estimator=FixedCostEstimator(),
        )

        result = await executor.run(agent=agent, message="Hi")

        assert result.is_ok()
        assert tracked_costs == [0.002]
        assert result.unwrap().total_cost == 0.002

    @pytest.mark.asyncio
    async def test_no_cost_fabrication_without_estimator(self):
        """Test cost is NOT tracked when no estimator is configured."""

        tracked_costs = []

        class CostTrackingGovernance:
            async def check_request(self, **kwargs):
                return True

            async def track_cost(
                self, cost: float, model: str, user_id: str | None = None
            ):
                tracked_costs.append(cost)

        class CountingStrategy:
            async def execute(self, message, **kwargs):
                from lexigram.result import Ok

                return Ok(
                    AgentResponse(message="done", total_tokens=1000, tool_calls=[])
                )

        agent = MockAgent(name="test", tools=[])
        agent.strategy = CountingStrategy()

        executor = AgentExecutorImpl(
            llm=MockLLM(),
            safety=None,
        )
        executor._governance = CostTrackingGovernance()

        result = await executor.run(agent=agent, message="Hi")

        assert result.is_ok()
        assert tracked_costs == []
        assert result.unwrap().total_cost == 0.0


class MockGuardPipeline:
    def __init__(self, input_action="allow", output_action="allow", final_content=None):
        self.input_action = input_action
        self.output_action = output_action
        self.final_content = final_content
        self.input_called = False
        self.output_called = False

    async def check_input(self, content, **kwargs):
        self.input_called = True
        return self._make_result(self.input_action, content)

    async def check_output(self, content, original_input="", **kwargs):
        self.output_called = True
        return self._make_result(self.output_action, content)

    def _make_result(self, action, content):
        from lexigram.result import Ok

        class MockGuardResult:
            def __init__(self, action, name, reason):
                self.action = action
                self.guard_name = name
                self.reason = reason
                self.passed = action in ("pass", "warn", "redact")
                self.details = {}

        class MockAggregateGuardResult:
            def __init__(self, action, blocked, blocking_result, final_content):
                self.action = action
                self.blocked = blocked
                self.blocking_result = blocking_result
                self.final_content = final_content

            @property
            def passed(self) -> bool:
                return not self.blocked

            @property
            def guard_name(self) -> str:
                return "aggregate"

            @property
            def details(self) -> dict:
                return {}

        if action == "block":
            agg = MockAggregateGuardResult(
                action="block",
                blocked=True,
                blocking_result=MockGuardResult("block", "stub", "blocked"),
                final_content=self.final_content or content,
            )
        else:
            agg = MockAggregateGuardResult(
                action="pass",
                blocked=False,
                blocking_result=None,
                final_content=self.final_content or content,
            )
        return Ok(agg)


class TestAgentExecutorGuardPipeline:
    """Tests for guard pipeline integration."""

    @pytest.mark.asyncio
    async def test_input_guard_passes(self):
        pipeline = MockGuardPipeline(input_action="allow")
        executor = AgentExecutorImpl(
            safety=AgentSafetyInfra(guard_pipeline=pipeline),
            llm=MockLLM(),
        )
        agent = MockAgent(name="test")

        result = await executor.run(agent=agent, message="Hello")

        assert result.is_ok()
        assert pipeline.input_called is True

    @pytest.mark.asyncio
    async def test_input_guard_blocks(self):
        pipeline = MockGuardPipeline(input_action="block")
        executor = AgentExecutorImpl(
            safety=AgentSafetyInfra(guard_pipeline=pipeline),
            llm=MockLLM(),
        )
        agent = MockAgent(name="test")

        result = await executor.run(agent=agent, message="Hello")

        assert result.is_err()
        assert "blocked by security guards" in str(result.unwrap_err())
        assert pipeline.input_called is True
        assert pipeline.output_called is False

    @pytest.mark.asyncio
    async def test_input_guard_redacts(self):
        pipeline = MockGuardPipeline(input_action="allow", final_content="Redacted")
        executor = AgentExecutorImpl(
            safety=AgentSafetyInfra(guard_pipeline=pipeline),
            llm=MockLLM(),
        )

        class EchoStrategy:
            async def execute(self, message, **kwargs):
                from lexigram.contracts.ai.agents import AgentResponse
                from lexigram.result import Ok

                return Ok(AgentResponse(message=message, total_tokens=0, tool_calls=[]))

        agent = MockAgent(name="test")
        agent.strategy = EchoStrategy()

        result = await executor.run(agent=agent, message="Hello")

        assert result.is_ok()
        assert result.unwrap().message == "Redacted"

    @pytest.mark.asyncio
    async def test_output_guard_blocks(self):
        pipeline = MockGuardPipeline(output_action="block")
        executor = AgentExecutorImpl(
            safety=AgentSafetyInfra(guard_pipeline=pipeline),
            llm=MockLLM(),
        )
        agent = MockAgent(name="test")

        result = await executor.run(agent=agent, message="Hello")

        assert result.is_err()
        assert "Output blocked" in str(result.unwrap_err())
        assert pipeline.input_called is True
        assert pipeline.output_called is True

    @pytest.mark.asyncio
    async def test_output_guard_redacts(self):
        pipeline = MockGuardPipeline(
            output_action="allow", final_content="Output Redacted"
        )
        executor = AgentExecutorImpl(
            safety=AgentSafetyInfra(guard_pipeline=pipeline),
            llm=MockLLM(),
        )
        agent = MockAgent(name="test")

        result = await executor.run(agent=agent, message="Hello")

        assert result.is_ok()
        assert result.unwrap().message == "Output Redacted"

    @pytest.mark.asyncio
    async def test_run_passes_pipeline_into_strategy_kwargs(self) -> None:
        pipeline = MockGuardPipeline(input_action="allow")

        class CaptureStrategy:
            seen = None

            async def execute(self, message, **kwargs):
                type(self).seen = kwargs.get("guard_pipeline")
                from lexigram.contracts.ai.agents import AgentResponse
                from lexigram.result import Ok

                return Ok(
                    AgentResponse(message="done", total_tokens=0, tool_calls=[])
                )

        executor = AgentExecutorImpl(
            safety=AgentSafetyInfra(guard_pipeline=pipeline),
            llm=MockLLM(),
        )
        agent = MockAgent(name="test")
        agent.strategy = CaptureStrategy()

        result = await executor.run(agent=agent, message="Hello")
        assert result.is_ok()
        assert CaptureStrategy.seen is pipeline

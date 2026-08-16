"""Unit tests for WorkflowEngine execution — linear, conditional, parallel,
cycles, human-in-the-loop, sub-workflows, timeouts, and validation.
"""

from __future__ import annotations

import pytest

from lexigram.workflow.config import GraphConfig
from lexigram.workflow.exceptions import (
    CycleDetectedError,
    GraphValidationError,
    HumanInputRequiredError,
    NodeExecutionError,
)
from lexigram.workflow.graph.edge import WorkflowEdge
from lexigram.workflow.graph.engine import WorkflowEngine
from lexigram.workflow.nodes.human_node import HumanNode
from lexigram.workflow.nodes.subworkflow_node import SubworkflowNode

from graph_helpers import AppendNode, ConstantNode, CounterNode, EchoNode, SlowNode


# ---------------------------------------------------------------------------
# Linear execution
# ---------------------------------------------------------------------------


class TestLinearWorkflow:
    @pytest.mark.asyncio
    async def test_linear_executes_all_three_nodes(
        self, linear_engine: WorkflowEngine
    ) -> None:
        result = await linear_engine.execute("start")
        assert result.is_ok()
        wf = result.unwrap()
        assert wf.final_state["path"] == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_linear_node_results_ordered(
        self, linear_engine: WorkflowEngine
    ) -> None:
        result = await linear_engine.execute("start")
        assert result.is_ok()
        wf = result.unwrap()
        names = [r.node_name for r in wf.node_results]
        assert names == ["a", "b", "c"]

    @pytest.mark.asyncio
    async def test_linear_all_node_results_succeeded(
        self, linear_engine: WorkflowEngine
    ) -> None:
        result = await linear_engine.execute("start")
        assert result.is_ok()
        wf = result.unwrap()
        assert all(r.succeeded for r in wf.node_results)

    @pytest.mark.asyncio
    async def test_linear_iterations_equals_node_count(
        self, linear_engine: WorkflowEngine
    ) -> None:
        result = await linear_engine.execute("start")
        assert result.is_ok()
        wf = result.unwrap()
        assert wf.iterations == 3

    @pytest.mark.asyncio
    async def test_linear_terminated_at_last_node(
        self, linear_engine: WorkflowEngine
    ) -> None:
        result = await linear_engine.execute("start")
        assert result.is_ok()
        assert result.unwrap().terminated_at == "c"

    @pytest.mark.asyncio
    async def test_linear_input_available_in_state(
        self, linear_engine: WorkflowEngine
    ) -> None:
        result = await linear_engine.execute("my_input")
        assert result.is_ok()
        assert result.unwrap().final_state["input"] == "my_input"

    @pytest.mark.asyncio
    async def test_linear_initial_state_passed_in(
        self, linear_engine: WorkflowEngine
    ) -> None:
        result = await linear_engine.execute("x", state={"extra": "data"})
        assert result.is_ok()
        assert result.unwrap().final_state["extra"] == "data"


# ---------------------------------------------------------------------------
# Conditional branching
# ---------------------------------------------------------------------------


class TestConditionalBranching:
    @pytest.mark.asyncio
    async def test_routes_to_b_when_route_equals_b(
        self, conditional_engine: WorkflowEngine
    ) -> None:
        result = await conditional_engine.execute("test")
        assert result.is_ok()
        wf = result.unwrap()
        names = [r.node_name for r in wf.node_results]
        assert "b" in names
        assert "c" not in names

    @pytest.mark.asyncio
    async def test_does_not_visit_inactive_branch(
        self, conditional_engine: WorkflowEngine
    ) -> None:
        result = await conditional_engine.execute("test")
        assert result.is_ok()
        assert result.unwrap().final_state.get("result") == "branch_b"

    @pytest.mark.asyncio
    async def test_routes_to_c_when_preset_route_is_c(self) -> None:
        nodes = {
            "a": ConstantNode("a", route="c", output="a_done"),
            "b": ConstantNode("b", result="branch_b", output="b_done"),
            "c": ConstantNode("c", result="branch_c", output="c_done"),
        }
        edges = [
            WorkflowEdge(source="a", target="b", condition=lambda s: s.get("route") == "b"),
            WorkflowEdge(source="a", target="c", condition=lambda s: s.get("route") == "c"),
        ]
        engine = WorkflowEngine(
            name="cond_c",
            nodes=nodes,
            edges=edges,
            entry_node="a",
            terminal_conditions={"b": None, "c": None},
        )
        result = await engine.execute("test")
        assert result.is_ok()
        wf = result.unwrap()
        names = [r.node_name for r in wf.node_results]
        assert "c" in names
        assert "b" not in names

    @pytest.mark.asyncio
    async def test_no_active_edge_stops_at_implicit_terminal(self) -> None:
        nodes = {
            "a": ConstantNode("a", route="unknown", output="a"),
            "b": ConstantNode("b", output="b"),
        }
        edges = [
            WorkflowEdge(source="a", target="b", condition=lambda s: s.get("route") == "b"),
        ]
        engine = WorkflowEngine(
            name="no_active_edge",
            nodes=nodes,
            edges=edges,
            entry_node="a",
            terminal_conditions={"b": None},
        )
        result = await engine.execute("test")
        assert result.is_ok()
        names = [r.node_name for r in result.unwrap().node_results]
        assert names == ["a"]


# ---------------------------------------------------------------------------
# Parallel execution
# ---------------------------------------------------------------------------


class TestParallelExecution:
    @pytest.mark.asyncio
    async def test_parallel_executes_both_branches(
        self, parallel_engine: WorkflowEngine
    ) -> None:
        result = await parallel_engine.execute("test")
        assert result.is_ok()
        names = [r.node_name for r in result.unwrap().node_results]
        assert "branch_a" in names
        assert "branch_b" in names

    @pytest.mark.asyncio
    async def test_parallel_executes_start_node_first(
        self, parallel_engine: WorkflowEngine
    ) -> None:
        result = await parallel_engine.execute("test")
        assert result.is_ok()
        names = [r.node_name for r in result.unwrap().node_results]
        assert names[0] == "start"

    @pytest.mark.asyncio
    async def test_parallel_branch_a_state_merged(
        self, parallel_engine: WorkflowEngine
    ) -> None:
        result = await parallel_engine.execute("test")
        assert result.is_ok()
        final_state = result.unwrap().final_state
        assert final_state.get("branch_a") is True

    @pytest.mark.asyncio
    async def test_parallel_branch_b_state_merged(
        self, parallel_engine: WorkflowEngine
    ) -> None:
        result = await parallel_engine.execute("test")
        assert result.is_ok()
        final_state = result.unwrap().final_state
        assert final_state.get("branch_b") is True

    @pytest.mark.asyncio
    async def test_parallel_total_node_count(
        self, parallel_engine: WorkflowEngine
    ) -> None:
        result = await parallel_engine.execute("test")
        assert result.is_ok()
        assert len(result.unwrap().node_results) == 3


# ---------------------------------------------------------------------------
# Cycle detection / max_iterations guard
# ---------------------------------------------------------------------------


class TestCycleDetection:
    @pytest.mark.asyncio
    async def test_cyclic_workflow_raises_cycle_detected_error(
        self, cyclic_engine: WorkflowEngine
    ) -> None:
        with pytest.raises(CycleDetectedError):
            await cyclic_engine.execute("test")

    @pytest.mark.asyncio
    async def test_cycle_error_carries_iteration_count(
        self, cyclic_engine: WorkflowEngine
    ) -> None:
        with pytest.raises(CycleDetectedError) as exc_info:
            await cyclic_engine.execute("test")
        assert exc_info.value.iterations == 3

    @pytest.mark.asyncio
    async def test_cycle_error_carries_node_name(
        self, cyclic_engine: WorkflowEngine
    ) -> None:
        with pytest.raises(CycleDetectedError) as exc_info:
            await cyclic_engine.execute("test")
        assert exc_info.value.node is not None

    @pytest.mark.asyncio
    async def test_custom_max_iterations_respected(self) -> None:
        nodes = {
            "a": CounterNode("a"),
            "b": EchoNode("b"),
        }
        edges = [
            WorkflowEdge(source="a", target="b"),
            WorkflowEdge(source="b", target="a"),
        ]
        engine = WorkflowEngine(
            name="custom_cycle",
            nodes=nodes,
            edges=edges,
            entry_node="a",
            terminal_conditions={},
            config=GraphConfig(max_iterations=5),
        )
        with pytest.raises(CycleDetectedError) as exc_info:
            await engine.execute("test")
        assert exc_info.value.iterations == 5

    @pytest.mark.asyncio
    async def test_cycle_with_conditional_exit_terminates_normally(self) -> None:
        nodes = {
            "counter": CounterNode("counter"),
            "check": ConstantNode("check", output="check"),
            "done": ConstantNode("done", finished=True, output="done"),
        }
        edges = [
            WorkflowEdge(source="counter", target="check"),
            WorkflowEdge(
                source="check",
                target="counter",
                condition=lambda s: s.get("count", 0) < 3,
            ),
            WorkflowEdge(
                source="check",
                target="done",
                condition=lambda s: s.get("count", 0) >= 3,
            ),
        ]
        engine = WorkflowEngine(
            name="conditional_cycle",
            nodes=nodes,
            edges=edges,
            entry_node="counter",
            terminal_conditions={"done": None},
            config=GraphConfig(max_iterations=20),
        )
        result = await engine.execute("test")
        assert result.is_ok()
        wf = result.unwrap()
        assert wf.final_state["count"] >= 3
        assert wf.terminated_at == "done"


# ---------------------------------------------------------------------------
# Human-in-the-loop
# ---------------------------------------------------------------------------


class TestHumanInTheLoop:
    @pytest.mark.asyncio
    async def test_raises_human_input_required(
        self, human_in_loop_engine: WorkflowEngine
    ) -> None:
        with pytest.raises(HumanInputRequiredError):
            await human_in_loop_engine.execute("ask me something")

    @pytest.mark.asyncio
    async def test_human_input_required_carries_node_name(
        self, human_in_loop_engine: WorkflowEngine
    ) -> None:
        with pytest.raises(HumanInputRequiredError) as exc_info:
            await human_in_loop_engine.execute("test")
        assert exc_info.value.node == "human"

    @pytest.mark.asyncio
    async def test_human_input_required_carries_rendered_prompt(
        self, human_in_loop_engine: WorkflowEngine
    ) -> None:
        with pytest.raises(HumanInputRequiredError) as exc_info:
            await human_in_loop_engine.execute("find_something")
        assert "find_something" in exc_info.value.prompt

    @pytest.mark.asyncio
    async def test_resume_continues_to_terminal(
        self, human_in_loop_engine: WorkflowEngine
    ) -> None:
        checkpoint_state = {
            "input": "test",
            "_paused_at": "human",
            "human_response": "my answer",
        }
        result = await human_in_loop_engine.resume(checkpoint_state, "my answer")
        assert result.is_ok()

    @pytest.mark.asyncio
    async def test_resume_injects_human_response_into_state(
        self, human_in_loop_engine: WorkflowEngine
    ) -> None:
        checkpoint_state = {
            "input": "test",
            "_paused_at": "human",
        }
        result = await human_in_loop_engine.resume(checkpoint_state, "operator_answer")
        assert result.is_ok()
        wf = result.unwrap()
        assert wf.final_state.get("human_response") == "operator_answer"

    @pytest.mark.asyncio
    async def test_resume_workflow_reaches_terminal(
        self, human_in_loop_engine: WorkflowEngine
    ) -> None:
        checkpoint_state = {"input": "test", "_paused_at": "human"}
        result = await human_in_loop_engine.resume(checkpoint_state, "yes")
        assert result.is_ok()
        wf = result.unwrap()
        assert wf.terminated_at == "end"

    @pytest.mark.asyncio
    async def test_direct_execute_with_human_response_in_state_skips_pause(
        self, human_in_loop_engine: WorkflowEngine
    ) -> None:
        result = await human_in_loop_engine.execute(
            "test", state={"human_response": "pre-answered"}
        )
        assert result.is_ok()
        wf = result.unwrap()
        assert wf.final_state.get("human_response") == "pre-answered"


# ---------------------------------------------------------------------------
# Sub-workflows
# ---------------------------------------------------------------------------


class TestSubWorkflow:
    @pytest.mark.asyncio
    async def test_subworkflow_is_visited_in_outer_node_results(self) -> None:
        inner_nodes = {
            "inner_a": ConstantNode("inner_a", inner_result="done", output="inner_out"),
        }
        inner_engine = WorkflowEngine(
            name="inner",
            nodes=inner_nodes,
            edges=[],
            entry_node="inner_a",
            terminal_conditions={"inner_a": None},
        )
        outer_nodes = {
            "start": ConstantNode("start", output="outer_start"),
            "sub": SubworkflowNode("sub", workflow=inner_engine),
            "end": ConstantNode("end", output="outer_end"),
        }
        outer_edges = [
            WorkflowEdge(source="start", target="sub"),
            WorkflowEdge(source="sub", target="end"),
        ]
        outer_engine = WorkflowEngine(
            name="outer",
            nodes=outer_nodes,
            edges=outer_edges,
            entry_node="start",
            terminal_conditions={"end": None},
        )
        result = await outer_engine.execute("parent_input")
        assert result.is_ok()
        names = [r.node_name for r in result.unwrap().node_results]
        assert names == ["start", "sub", "end"]

    @pytest.mark.asyncio
    async def test_subworkflow_output_stored_in_outer_state(self) -> None:
        inner_nodes = {"calc": ConstantNode("calc", output="inner_result_value")}
        inner_engine = WorkflowEngine(
            name="inner_calc",
            nodes=inner_nodes,
            edges=[],
            entry_node="calc",
            terminal_conditions={"calc": None},
        )
        outer_nodes = {
            "sub": SubworkflowNode("sub", workflow=inner_engine, output_key="sub_out"),
            "terminal": ConstantNode("terminal", output="done"),
        }
        outer_engine = WorkflowEngine(
            name="outer_calc",
            nodes=outer_nodes,
            edges=[WorkflowEdge(source="sub", target="terminal")],
            entry_node="sub",
            terminal_conditions={"terminal": None},
        )
        result = await outer_engine.execute("test")
        assert result.is_ok()
        wf = result.unwrap()
        assert wf.final_state.get("sub_out") == "inner_result_value"

    @pytest.mark.asyncio
    async def test_nested_subworkflow_returns_ok_on_inner_failure(self) -> None:
        class _FailEngine:
            name = "fail_inner"

            async def execute(self, input_: str, *, state=None) -> object:
                from lexigram.result import Err as ErrT

                return ErrT(RuntimeError("inner boom"))

        outer_nodes = {
            "sub": SubworkflowNode("sub", workflow=_FailEngine(), output_key="sub_result"),
            "end": ConstantNode("end", output="ok"),
        }
        outer_engine = WorkflowEngine(
            name="outer_fail",
            nodes=outer_nodes,
            edges=[WorkflowEdge(source="sub", target="end")],
            entry_node="sub",
            terminal_conditions={"end": None},
        )
        result = await outer_engine.execute("test")
        assert result.is_ok()
        wf = result.unwrap()
        assert "Subworkflow error" in str(wf.final_state.get("sub_result", ""))


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


class TestWorkflowEngineValidation:
    def test_validate_raises_when_entry_node_not_registered(self) -> None:
        engine = WorkflowEngine(
            name="invalid",
            nodes={"a": EchoNode("a")},
            edges=[],
            entry_node="nonexistent",
            terminal_conditions={"a": None},
        )
        with pytest.raises(GraphValidationError):
            engine.validate()

    def test_validate_raises_when_terminal_node_not_registered(self) -> None:
        engine = WorkflowEngine(
            name="invalid",
            nodes={"a": EchoNode("a")},
            edges=[],
            entry_node="a",
            terminal_conditions={"ghost": None},
        )
        with pytest.raises(GraphValidationError):
            engine.validate()

    def test_validate_raises_when_edge_source_not_registered(self) -> None:
        engine = WorkflowEngine(
            name="invalid",
            nodes={"b": EchoNode("b")},
            edges=[WorkflowEdge(source="missing", target="b")],
            entry_node="b",
            terminal_conditions={"b": None},
        )
        with pytest.raises(GraphValidationError):
            engine.validate()

    def test_validate_raises_when_edge_target_not_registered(self) -> None:
        engine = WorkflowEngine(
            name="invalid",
            nodes={"a": EchoNode("a")},
            edges=[WorkflowEdge(source="a", target="missing")],
            entry_node="a",
            terminal_conditions={"a": None},
        )
        with pytest.raises(GraphValidationError):
            engine.validate()

    def test_validate_passes_for_valid_single_node_workflow(self) -> None:
        engine = WorkflowEngine(
            name="solo",
            nodes={"only": EchoNode("only")},
            edges=[],
            entry_node="only",
            terminal_conditions={"only": None},
        )
        engine.validate()  # must not raise


# ---------------------------------------------------------------------------
# Engine properties
# ---------------------------------------------------------------------------


class TestWorkflowEngineProperties:
    def test_name_property_returns_engine_name(self) -> None:
        engine = WorkflowEngine(
            name="my_workflow",
            nodes={"a": EchoNode("a")},
            edges=[],
            entry_node="a",
            terminal_conditions={"a": None},
        )
        assert engine.name == "my_workflow"


# ---------------------------------------------------------------------------
# Node execution failures
# ---------------------------------------------------------------------------


class TestNodeExecutionFailure:
    @pytest.mark.asyncio
    async def test_failing_node_raises_node_execution_error(self) -> None:
        from graph_helpers import FailingNode

        nodes = {"bad": FailingNode("bad", message="test failure")}
        engine = WorkflowEngine(
            name="fail_test",
            nodes=nodes,
            edges=[],
            entry_node="bad",
            terminal_conditions={"bad": None},
        )
        with pytest.raises(NodeExecutionError) as exc_info:
            await engine.execute("test")
        assert "test failure" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_node_execution_error_carries_node_name(self) -> None:
        from graph_helpers import FailingNode

        nodes = {"broken": FailingNode("broken")}
        engine = WorkflowEngine(
            name="broken_workflow",
            nodes=nodes,
            edges=[],
            entry_node="broken",
            terminal_conditions={"broken": None},
        )
        with pytest.raises(NodeExecutionError) as exc_info:
            await engine.execute("test")
        assert exc_info.value.node == "broken"


# ---------------------------------------------------------------------------
# Node timeout
# ---------------------------------------------------------------------------


class TestNodeTimeout:
    @pytest.mark.asyncio
    async def test_slow_node_returns_err_when_node_timeout_exceeded(self) -> None:
        nodes = {"slow": SlowNode("slow", delay=5.0)}
        engine = WorkflowEngine(
            name="timeout_test",
            nodes=nodes,
            edges=[],
            entry_node="slow",
            terminal_conditions={"slow": None},
            config=GraphConfig(node_timeout=0.01),
        )
        with pytest.raises(NodeExecutionError) as exc_info:
            await engine.execute("test")
        assert "timed out" in str(exc_info.value).lower()

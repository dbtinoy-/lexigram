"""Tests for workflow module."""

import pytest
from lexigram.workflow import WorkflowModule
from lexigram.di.module import DynamicModule


class TestWorkflowModule:
    def test_workflow_module_exists(self) -> None:
        assert WorkflowModule is not None

    def test_configure_returns_dynamic_module(self) -> None:
        result = WorkflowModule.configure()
        assert isinstance(result, DynamicModule)
        assert result.module is WorkflowModule

    def test_configure_exports_pipeline_protocol(self) -> None:
        from lexigram.contracts.workflow import PipelineProtocol

        result = WorkflowModule.configure()
        assert PipelineProtocol in result.exports

    def test_configure_config_type_check(self) -> None:
        with pytest.raises(TypeError, match="must be BulkOperationConfig"):
            WorkflowModule.configure(config="invalid")

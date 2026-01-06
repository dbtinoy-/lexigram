"""Workflow CLI contributor definitions."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import (
    CommandContribution,
    HealthCheckContribution,
    ShellContextContribution,
)
from lexigram.contracts.cli.types import GeneratorDefinition

_GENERATOR_DEFINITIONS: tuple[GeneratorDefinition, ...] = (
    GeneratorDefinition(
        name="workflow_def",
        title="Generate Workflow Definition",
        description="Generate a workflow definition with steps and transitions",
        contributor="workflow",
        generator_path="lexigram.workflow.cli.generators.workflow_def:WorkflowDefinitionGenerator",
        default_output_dir="src/workflows",
        category="workflow",
    ),
    GeneratorDefinition(
        name="pipeline",
        title="Generate Pipeline",
        description="Generate a pipeline with sequential processing stages",
        contributor="workflow",
        generator_path="lexigram.workflow.cli.generators.pipeline:PipelineGenerator",
        default_output_dir="src/pipelines",
        category="workflow",
    ),
    GeneratorDefinition(
        name="saga_step",
        title="Generate Saga Step",
        description="Generate a saga step with compensating transaction",
        contributor="workflow",
        generator_path="lexigram.workflow.cli.generators.saga_step:SagaStepGenerator",
        default_output_dir="src/sagas",
        category="workflow",
    ),
)


class WorkflowCliContributor:
    """CLI contributor for the lexigram-workflow package."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "workflow"

    def get_generators(self) -> list[GeneratorDefinition]:
        """Return generator definitions for workflow."""
        return list(_GENERATOR_DEFINITIONS)

    def get_commands(self) -> list[CommandContribution]:
        """Return the contributed `workflow` command group."""
        return [
            CommandContribution(
                name="workflow",
                help="Workflow and pipeline management commands",
                app_factory_path="lexigram.workflow.cli.commands:create_workflow_app",
                contributor="workflow",
                category="workflow",
                requires_app_context=True,
            ),
        ]

    def get_health_checks(self) -> list[HealthCheckContribution]:
        """Return workflow engine health check."""
        return [
            HealthCheckContribution(
                name="workflow_engine_status",
                description="Verify workflow engine is operational",
                check_path="lexigram.workflow.cli.checks:check_workflow_engine",
                contributor="workflow",
                category="workflow",
                timeout=5.0,
            ),
        ]

    def get_doctor_checks(self) -> list:
        """Return no doctor check contributions."""
        return []

    def get_shell_context(self) -> list[ShellContextContribution]:
        """Return workflow engine shell context."""
        return [
            ShellContextContribution(
                name="workflow",
                description="Workflow engine for interactive use",
                factory_path="lexigram.workflow.cli.shell:provide_workflow_engine",
                contributor="workflow",
            ),
        ]

    def get_hooks(self) -> list:
        """Return no hook contributions."""
        return []


__all__ = ["WorkflowCliContributor"]

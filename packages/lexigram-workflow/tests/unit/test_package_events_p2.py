"""P2 guardrail: lexigram-workflow must expose a canonical root events module."""

from __future__ import annotations


def test_workflow_events_root_module_exists() -> None:
    from lexigram.workflow.events import (
        WorkflowCompletedEvent,
        WorkflowFailedEvent,
        WorkflowStartedEvent,
    )

    assert WorkflowStartedEvent.__name__ == "WorkflowStartedEvent"
    assert WorkflowCompletedEvent.__name__ == "WorkflowCompletedEvent"
    assert WorkflowFailedEvent.__name__ == "WorkflowFailedEvent"


def test_workflow_events_re_exported_from_package_root() -> None:
    import lexigram.workflow as workflow_pkg

    assert hasattr(workflow_pkg, "WorkflowStartedEvent")
    assert hasattr(workflow_pkg, "WorkflowCompletedEvent")
    assert hasattr(workflow_pkg, "WorkflowFailedEvent")

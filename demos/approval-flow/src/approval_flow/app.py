"""Composition root for the single-niche Approval Flow demo."""

from __future__ import annotations

from approval_flow.controllers.api import ApprovalFlowApiController
from approval_flow.di.provider import ApprovalFlowProvider
from approval_flow.services.flow import build_approval_state_machine
from approval_flow.ui.pages import ApprovalFlowPageController
from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.di.provider import Provider
from lexigram.web.module import WebModule
from lexigram.workflow.module import WorkflowModule


def build_modules() -> list[object]:
    return [
        WorkflowModule.configure(state_machine=build_approval_state_machine()),
        WebModule.configure(
            controllers=[ApprovalFlowApiController, ApprovalFlowPageController],
        ),
    ]


def build_providers() -> list[Provider]:
    return [ApprovalFlowProvider()]


def create_app(config: LexigramConfig | None = None) -> Application:
    app = Application(name="approval-flow", config=config)
    app.add_modules(build_modules())
    app.add_providers(build_providers())
    return app


__all__ = ["build_modules", "build_providers", "create_app"]

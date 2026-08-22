"""Root module for the ai-guardrails demo."""

from __future__ import annotations

import os

from lexigram.ai.guard.config import GuardConfig
from lexigram.ai.guard.module import GuardModule
from lexigram.ai.governance.config import GovernanceConfig
from lexigram.ai.governance.module import GovernanceModule
from lexigram.di.module import DynamicModule, Module, module
from lexigram.web import WebConfig, WebModule
from lexigram.web.config import ServerConfig
from lexigram.web.security import SecurityConfig

from guard_gate.acts import RESTRICTED_MODEL
from guard_gate.assistant_service import GuardedAssistant
from guard_gate.controllers.api import GuardApiController
from guard_gate.di.provider import GuardrailsProvider
from guard_gate.policy import PolicyToggle
from guard_gate.ui.pages import PlaygroundPageController


@module()
class GuardrailsModule(Module):
    """Guarded assistant playground with governance budgets."""

    @classmethod
    def configure(cls, port: int | None = None) -> DynamicModule:
        selected_port = port if port is not None else int(
            os.environ.get("GUARD_GATE_PORT", "8084")
        )
        return DynamicModule(
            module=cls,
            imports=[
                GuardModule.configure(GuardConfig(
                    injection_detection=True,
                    injection_action="block",
                    pii_detection=True,
                    pii_action="redact",
                    pii_redaction_output=True,
                    max_input_chars=500,
                    length_action="block",
                )),
                GovernanceModule.configure(GovernanceConfig(
                    monthly_budget=0.50,
                    restricted_models=[RESTRICTED_MODEL],
                )),
                WebModule.configure(
                    controllers=[GuardApiController, PlaygroundPageController],
                    web_config=WebConfig(
                        server=ServerConfig(host="127.0.0.1", port=selected_port),
                        security=SecurityConfig(enable_csrf=False),
                    ),
                ),
            ],
            providers=[GuardrailsProvider],
            exports=[GuardedAssistant, PolicyToggle],
        )


__all__ = ["GuardrailsModule"]

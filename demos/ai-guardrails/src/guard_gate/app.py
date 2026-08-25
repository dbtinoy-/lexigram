"""Application composition root for the ai-guardrails demo."""

from __future__ import annotations

from guard_gate.config import load_lex_config
from guard_gate.controllers.api import GuardApiController
from guard_gate.di.provider import GuardrailsProvider
from guard_gate.repository.acts import RESTRICTED_MODEL
from guard_gate.ui.pages import PlaygroundPageController
from lexigram.ai.governance.config import GovernanceConfig
from lexigram.ai.governance.module import GovernanceModule
from lexigram.ai.guard.config import GuardConfig
from lexigram.ai.guard.module import GuardModule
from lexigram.app.base import Application
from lexigram.config.main import LexigramConfig
from lexigram.web.config import WebConfig
from lexigram.web.module import WebModule


def create_app(config: LexigramConfig | None = None) -> Application:
    """Create the configured (not yet started) guardrails application."""
    config = config or load_lex_config()
    web_config = config.get_section("web", WebConfig)

    app = Application(name="ai-guardrails", config=config)
    app.add_modules(
        [
            GuardModule.configure(
                GuardConfig(
                    injection_detection=True,
                    injection_action="block",
                    pii_detection=True,
                    pii_action="redact",
                    pii_redaction_output=True,
                    max_input_chars=500,
                    length_action="block",
                )
            ),
            GovernanceModule.configure(
                GovernanceConfig(
                    monthly_budget=0.50,
                    restricted_models=[RESTRICTED_MODEL],
                )
            ),
            WebModule.configure(
                web_config=web_config,
                controllers=[GuardApiController, PlaygroundPageController],
            ),
        ]
    )
    app.add_provider(GuardrailsProvider())
    return app


__all__ = ["create_app"]

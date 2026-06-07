"""CLI contributions for lexigram-ai-session."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import SchemaSetupContribution


class AiSessionCliContributor:
    """CLI contributions for lexigram-ai-session."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "ai-session"

    def get_schema_setup(self) -> list[SchemaSetupContribution]:
        """Return schema setup contributions for ai-session."""
        return [
            SchemaSetupContribution(
                name="ai_session.session_tables",
                description="AI session and checkpoint storage",
                setup_fn_path="lexigram.ai.session.cli.schema_setup:ensure_session_tables",
                contributor=self.contributor_id,
            ),
        ]


__all__ = ["AiSessionCliContributor"]

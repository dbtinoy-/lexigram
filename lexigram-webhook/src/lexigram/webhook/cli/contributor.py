"""CLI contributions for lexigram-webhook."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import SchemaSetupContribution


class WebhookCliContributor:
    """CLI contributions for lexigram-webhook."""

    @property
    def contributor_id(self) -> str:
        """Return the contributor identifier."""
        return "webhook"

    def get_schema_setup(self) -> list[SchemaSetupContribution]:
        """Return schema setup contributions for webhook."""
        return [
            SchemaSetupContribution(
                name="webhook.subscriptions",
                description="Webhook subscription storage",
                setup_fn_path="lexigram.webhook.cli.schema_setup:ensure_subscriptions",
                contributor=self.contributor_id,
            ),
            SchemaSetupContribution(
                name="webhook.delivery_attempts",
                description="Webhook delivery attempt storage",
                setup_fn_path="lexigram.webhook.cli.schema_setup:ensure_delivery_attempts",
                contributor=self.contributor_id,
            ),
        ]


__all__ = ["WebhookCliContributor"]

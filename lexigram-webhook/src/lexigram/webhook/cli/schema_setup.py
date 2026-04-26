"""Schema setup contributions for the lexigram-webhook package."""

from __future__ import annotations

from lexigram.contracts.cli.contributions import SchemaSetupOutcome, SchemaSetupResult
from lexigram.contracts.data.sql.database import DatabaseProviderProtocol

_SUBSCRIPTIONS_TABLE = "webhook_subscriptions"
_DELIVERY_ATTEMPTS_TABLE = "webhook_delivery_attempts"


async def ensure_subscriptions(db: DatabaseProviderProtocol) -> SchemaSetupOutcome:
    """Ensure the ``webhook_subscriptions`` table exists.

    Args:
        db: The database provider.

    Returns:
        Outcome reporting CREATED, ALREADY_PRESENT, or FAILED.
    """
    from lexigram.webhook.store.sql import SqlWebhookSubscriptionStore

    try:
        existed = await db.table_exists(_SUBSCRIPTIONS_TABLE)
        await SqlWebhookSubscriptionStore(db).initialize()
        return SchemaSetupOutcome(
            status=(
                SchemaSetupResult.ALREADY_PRESENT
                if existed
                else SchemaSetupResult.CREATED
            )
        )
    except Exception as exc:
        return SchemaSetupOutcome(status=SchemaSetupResult.FAILED, message=str(exc))


async def ensure_delivery_attempts(db: DatabaseProviderProtocol) -> SchemaSetupOutcome:
    """Ensure the ``webhook_delivery_attempts`` table exists.

    Args:
        db: The database provider.

    Returns:
        Outcome reporting CREATED, ALREADY_PRESENT, or FAILED.
    """
    from lexigram.webhook.store.sql import SqlWebhookDeliveryStore

    try:
        existed = await db.table_exists(_DELIVERY_ATTEMPTS_TABLE)
        await SqlWebhookDeliveryStore(db).initialize()
        return SchemaSetupOutcome(
            status=(
                SchemaSetupResult.ALREADY_PRESENT
                if existed
                else SchemaSetupResult.CREATED
            )
        )
    except Exception as exc:
        return SchemaSetupOutcome(status=SchemaSetupResult.FAILED, message=str(exc))

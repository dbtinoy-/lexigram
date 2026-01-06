"""
Example: Structured Logging

Demonstrates how to use Lexigram's structured logging throughout an app.
- Import logger from lexigram.logging
- Structured key-value logging (not f-strings)
- Works across all services
"""

from __future__ import annotations

import asyncio
from typing import Protocol

from lexigram.app import Application
from lexigram.di import Provider, Module
from lexigram.di.module import module as di_module
from lexigram.logging import get_logger


logger = get_logger(__name__)


class PaymentProcessorProtocol(Protocol):
    async def process(self, user_id: str, amount: float) -> bool: ...


class PaymentProcessor:
    async def process(self, user_id: str, amount: float) -> bool:
        logger.info("payment_processing_start", user_id=user_id, amount_usd=amount)

        # Simulate processing
        await asyncio.sleep(0.1)

        if amount > 10000:
            logger.warning(
                "payment_suspicious",
                user_id=user_id,
                amount_usd=amount,
                reason="high_value"
            )
            return False

        logger.info("payment_processed", user_id=user_id, amount_usd=amount, status="success")
        return True


class BillingServiceProtocol(Protocol):
    async def charge_user(self, user_id: str, amount: float) -> bool: ...


class BillingService:
    def __init__(self, processor: PaymentProcessorProtocol):
        self.processor = processor
        self.logger = get_logger(__name__)

    async def charge_user(self, user_id: str, amount: float) -> bool:
        self.logger.info("billing_start", user_id=user_id, amount_usd=amount)

        try:
            success = await self.processor.process(user_id, amount)
            if success:
                self.logger.info("billing_success", user_id=user_id, amount_usd=amount)
            else:
                self.logger.error("billing_failed", user_id=user_id, amount_usd=amount, reason="processor_rejected")
            return success
        except Exception as e:
            self.logger.error("billing_error", user_id=user_id, amount_usd=amount, error=str(e))
            return False


class BillingProvider(Provider):
    name = "billing"

    async def register(self, container):
        container.singleton(PaymentProcessorProtocol, PaymentProcessor)
        container.singleton(BillingServiceProtocol, BillingService)


@di_module(providers=[BillingProvider], exports=[BillingServiceProtocol])
class BillingModule(Module):
    pass


async def main():
    async with Application.boot(modules=[BillingModule]) as app:
        service = await app.container.resolve(BillingServiceProtocol)

        # Successful charge
        await service.charge_user("user_123", 99.99)

        # Rejected charge
        await service.charge_user("user_456", 50000.00)


if __name__ == "__main__":
    asyncio.run(main())

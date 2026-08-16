"""NotificationModule — IoC module for lexigram-notification."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.notification.protocols import (
    PushChannelProtocol,
    SMSChannelProtocol,
)
from lexigram.di.module import DynamicModule, Module, module

if TYPE_CHECKING:
    from lexigram.notification.config import NotificationConfig


@module()
class NotificationModule(Module):
    """SMS and push notification integration with Named DI multi-backend support.

    Registers :class:`~lexigram.contracts.notification.protocols.SMSChannelProtocol`
    and :class:`~lexigram.contracts.notification.protocols.PushChannelProtocol` for
    constructor injection.

    Usage::

        from lexigram.notification.config import NotificationConfig
        from lexigram.notification.module import NotificationModule

        @module(
            imports=[NotificationModule.configure(NotificationConfig(backends=[...]))]
        )
        class AppModule(Module):
            pass

    Named injection::

        class MyService:
            def __init__(
                self,
                sms: SMSChannelProtocol,                                    # primary
                alerts_sms: Annotated[SMSChannelProtocol, Named("alerts")], # named
                push: PushChannelProtocol,                                   # primary
                mobile_push: Annotated[PushChannelProtocol, Named("mobile")], # named
            ) -> None: ...
    """

    @classmethod
    def configure(cls, config: NotificationConfig | Any | None = None) -> DynamicModule:
        """Create a NotificationModule with explicit configuration.

        Args:
            config: :class:`~lexigram.notification.config.NotificationConfig` or ``None``
                to use defaults (reads from environment variables).

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.notification.di.provider import NotificationProvider

        return DynamicModule(
            module=cls,
            providers=[NotificationProvider(config=config)],
            exports=[SMSChannelProtocol, PushChannelProtocol],
        )

    @classmethod
    def stub(cls, config: Any = None) -> DynamicModule:
        """Return a NotificationModule for unit tests — no messages sent.

        Uses an empty config (no backends configured) so all notifications
        are dropped and no external services are contacted.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.notification.config import NotificationConfig
        from lexigram.notification.di.provider import NotificationProvider

        return DynamicModule(
            module=cls,
            providers=[NotificationProvider(config=NotificationConfig())],
            exports=[SMSChannelProtocol, PushChannelProtocol],
        )


__all__ = ["NotificationModule"]

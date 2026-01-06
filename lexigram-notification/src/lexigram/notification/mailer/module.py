"""MailerModule — IoC module for email delivery."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.mailer.protocols import MailerProtocol
from lexigram.di.module import DynamicModule, Module, module

if TYPE_CHECKING:
    from lexigram.notification.config import MailerConfig


@module()
class MailerModule(Module):
    """Email delivery integration with Named DI multi-backend support.

    Registers :class:`~lexigram.contracts.mailer.protocols.MailerProtocol` for
    constructor injection, supporting SMTP and SendGrid backends.

    Usage::

        from lexigram.notification.config import MailerConfig, NamedMailerConfig
        from lexigram.notification.mailer.module import MailerModule

        @module(
            imports=[
                MailerModule.configure(
                    MailerConfig(
                        backends=[
                            NamedMailerConfig(
                                name="transactional",
                                primary=True,
                                driver="sendgrid",
                            )
                        ]
                    )
                )
            ]
        )
        class AppModule(Module):
            pass

    Named injection::

        class MyService:
            def __init__(
                self,
                mailer: MailerProtocol,                                          # primary
                bulk: Annotated[MailerProtocol, Named("bulk")],                  # named
            ) -> None: ...
    """

    @classmethod
    def configure(cls, config: MailerConfig | Any | None = None) -> DynamicModule:
        """Create a MailerModule with explicit configuration.

        Args:
            config: :class:`~lexigram.notification.config.MailerConfig` or ``None``
                to use defaults (no backends).

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.notification.di.mailer_provider import MailerProvider

        return DynamicModule(
            module=cls,
            providers=[MailerProvider(config=config)],
            exports=[MailerProtocol],
        )

    @classmethod
    def stub(cls, config: MailerConfig | Any | None = None) -> DynamicModule:
        """Return a MailerModule for unit tests — no emails sent.

        Uses an empty config (no backends configured) so all mail operations
        are dropped and no external services are contacted.

        Args:
            config: Optional :class:`~lexigram.notification.config.MailerConfig`
                for test scenarios that need specific stubs.

        Returns:
            A :class:`~lexigram.di.module.DynamicModule` descriptor.
        """
        from lexigram.notification.config import MailerConfig as _MailerConfig
        from lexigram.notification.di.mailer_provider import MailerProvider

        return DynamicModule(
            module=cls,
            providers=[MailerProvider(config=config or _MailerConfig())],
            exports=[MailerProtocol],
        )


__all__ = ["MailerModule"]

"""MailerProvider — DI provider for email delivery backends."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.contracts.core import HealthCheckResult, HealthStatus, ProviderPriority
from lexigram.contracts.mailer.protocols import MailerProtocol
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.notification.config import (
    MailerConfig,
    NamedMailerConfig,
    SendGridDriverConfig,
    SMTPDriverConfig,
)

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


class MailerProvider(Provider):
    """Register SMTP and SendGrid mailer backends into the DI container.

    Reads :class:`~lexigram.notification.config.MailerConfig`, creates the
    appropriate mailer backends, and registers them as
    :class:`~lexigram.contracts.mailer.protocols.MailerProtocol`.

    Configuration is explicit-only: ``MailerConfig`` is not bound to a
    ``LexigramConfig`` section, so this provider declares no
    ``config_key``/``config_model`` attributes.

    Supports multi-backend (``MailerConfig.backends``) mode. Each entry is
    registered under its name via ``container.singleton(name=entry.name)``.
    The primary backend (``primary=True`` or the first entry) also receives
    the unnamed binding for constructor injection without ``Named``.
    """

    name = "mailer"
    priority = ProviderPriority.INFRASTRUCTURE

    def __init__(self, config: MailerConfig | None = None) -> None:
        super().__init__()
        self._config = config or MailerConfig()
        self._mailers: list[tuple[str, Any]] = []

    @classmethod
    def from_config(cls, config: MailerConfig, **context: Any) -> MailerProvider:
        """Factory method for DI container setup.

        Args:
            config: Mailer configuration.
            **context: Ignored extra context.

        Returns:
            A new :class:`MailerProvider` instance.
        """
        return cls(config)

    def _create_mailer(self, entry: NamedMailerConfig) -> Any:
        """Instantiate the correct mailer implementation for a config entry.

        Args:
            entry: Named mailer configuration entry.

        Returns:
            A mailer instance conforming to :class:`MailerProtocol`.

        Raises:
            ValueError: When the driver name is not recognised.
        """
        from lexigram.notification.mailer.smtp_mailer import SMTPMailer

        if entry.driver == "smtp":
            cfg = entry.smtp or SMTPDriverConfig()
            password: str | None = None
            if cfg.password:
                password = getattr(
                    cfg.password, "get_secret_value", lambda: cfg.password or ""
                )()
            return SMTPMailer(
                host=cfg.host,
                port=cfg.port,
                username=cfg.username,
                password=password,
                use_tls=cfg.use_tls,
                use_ssl=cfg.use_ssl,
                timeout=cfg.timeout,
                from_email=entry.from_email,
            )

        if entry.driver == "sendgrid":
            from lexigram.notification.mailer.sendgrid_mailer import SendGridMailer

            cfg_sg = entry.sendgrid or SendGridDriverConfig()
            api_key: str = ""
            if cfg_sg.api_key:
                api_key = (
                    getattr(
                        cfg_sg.api_key, "get_secret_value", lambda: cfg_sg.api_key or ""
                    )()
                    or ""
                )
            return SendGridMailer(
                api_key=api_key,
                timeout=cfg_sg.timeout,
                sandbox_mode=cfg_sg.sandbox_mode,
                from_email=entry.from_email,
            )

        if entry.driver == "console":
            from lexigram.notification.mailer.console_mailer import ConsoleMailer

            return ConsoleMailer()

        raise ValueError(f"Unsupported mailer driver: {entry.driver!r}")

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind all mailer backends into the container.

        When no backends are configured and ``console_fallback`` is enabled,
        a :class:`~lexigram.notification.mailer.console_mailer.ConsoleMailer`
        is bound as the default ``MailerProtocol`` so outgoing emails are
        logged to the console instead of being silently dropped.

        Args:
            container: DI registrar received from the framework.
        """
        container.singleton(MailerConfig, self._config)

        for entry in self._config.backends:
            mailer = self._create_mailer(entry)
            self._mailers.append((entry.name, mailer))
            container.singleton(
                MailerProtocol,
                factory=lambda _resolver, m=mailer: m,
                name=entry.name,
            )
            is_primary = entry.primary or (
                not any(e.primary for e in self._config.backends)
                and self._config.backends[0] is entry
            )
            if is_primary:
                container.singleton(
                    MailerProtocol, factory=lambda _resolver, m=mailer: m
                )

        if not self._config.backends and self._config.console_fallback:
            from lexigram.notification.mailer.console_mailer import ConsoleMailer

            console = ConsoleMailer()
            self._mailers.append(("console", console))
            container.singleton(
                MailerProtocol,
                factory=lambda _resolver, m=console: m,
            )

        logger.info(
            "mailer_registered",
            backends=[n for n, _ in self._mailers],
        )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """No-op boot; mailers are stateless and require no startup.

        Args:
            container: DI resolver (unused).
        """

    async def shutdown(self) -> None:
        """Clear registered mailer references."""
        self._mailers.clear()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Aggregate health across all registered mailer backends.

        Args:
            timeout: Per-backend health-check timeout in seconds.

        Returns:
            :class:`~lexigram.contracts.core.HealthCheckResult`.
        """
        import asyncio

        if not self._mailers:
            return HealthCheckResult(
                component="mailer",
                status=HealthStatus.HEALTHY,
                details={"backends": []},
            )

        results = await asyncio.gather(
            *[
                svc.health_check(timeout=timeout)
                for _, svc in self._mailers
                if hasattr(svc, "health_check")
            ],
            return_exceptions=True,
        )
        worst = HealthStatus.HEALTHY
        details: dict[str, Any] = {}
        for (name, _), result in zip(self._mailers, results, strict=False):
            if isinstance(result, Exception):
                worst = HealthStatus.UNHEALTHY
                details[name] = {"status": "error", "error": str(result)}
            elif isinstance(result, HealthCheckResult):
                details[name] = {"status": result.status.value}
                if result.status == HealthStatus.UNHEALTHY:
                    worst = HealthStatus.UNHEALTHY
                elif (
                    result.status == HealthStatus.DEGRADED
                    and worst == HealthStatus.HEALTHY
                ):
                    worst = HealthStatus.DEGRADED

        return HealthCheckResult(
            component="mailer",
            status=worst,
            details=details,
        )


__all__ = ["MailerProvider"]

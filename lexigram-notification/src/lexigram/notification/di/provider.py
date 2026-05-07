"""DI provider for lexigram-notification."""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from lexigram.contracts.core import HealthCheckResult, HealthStatus, ProviderPriority
from lexigram.contracts.notification.protocols import (
    PushChannelProtocol,
    SMSChannelProtocol,
)
from lexigram.di.provider import Provider
from lexigram.logging import get_logger
from lexigram.notification.config import (
    APNsDriverConfig,
    FCMDriverConfig,
    NamedPushConfig,
    NamedSMSConfig,
    NotificationConfig,
    TwilioDriverConfig,
    WebPushDriverConfig,
)

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)

try:
    from lexigram.notification.backends.sms.twilio import TwilioSMS
except ImportError:
    TwilioSMS = None  # type: ignore[assignment,misc]

try:
    from lexigram.notification.backends.push.fcm import FCMPush
except ImportError:
    FCMPush = None  # type: ignore[assignment,misc]

try:
    from lexigram.notification.backends.push.apns import APNsPush
except ImportError:
    APNsPush = None  # type: ignore[assignment,misc]

try:
    from lexigram.notification.backends.push.web_push import WebPushChannel
except ImportError:
    WebPushChannel = None  # type: ignore[assignment,misc]


class NotificationProvider(Provider):
    """Register SMS and push notification services into the DI container.

    Reads :class:`~lexigram.notification.config.NotificationConfig`, creates
    the appropriate backends, and registers them as ``SMSChannelProtocol`` and
    ``PushChannelProtocol``.

    Supports multi-backend (``NotificationConfig.sms_backends`` and
    ``NotificationConfig.push_backends``) mode. Each entry is registered under
    its name via ``container.singleton(name=entry.name)``. The primary backend
    (``primary=True`` or the first entry) also receives the unnamed bindings
    for backward compatibility.
    """

    name = "notification"
    priority = ProviderPriority.INFRASTRUCTURE
    config_key: str | None = "notification"
    config_model: type | None = NotificationConfig

    def __init__(self, config: NotificationConfig | None = None) -> None:
        super().__init__()
        self._requested_config = config
        self._config = config or NotificationConfig()
        self._sms_services: list[tuple[str, Any]] = []
        self._push_services: list[tuple[str, Any]] = []

    @classmethod
    def from_config(
        cls, config: NotificationConfig, **context: Any
    ) -> NotificationProvider:
        """Factory method for DI container setup."""
        return cls(config)

    def _create_sms(self, entry: NamedSMSConfig) -> Any:
        """Instantiate the correct SMS implementation for a config."""
        if entry.driver == "twilio":
            if TwilioSMS is None:
                raise ImportError("TwilioSMS unavailable")
            cfg = entry.twilio or TwilioDriverConfig()
            token = getattr(
                cfg.auth_token, "get_secret_value", lambda: cfg.auth_token
            )()
            return TwilioSMS(
                account_sid=cfg.account_sid or "",
                auth_token=token or "",
                from_number=cfg.from_number,
                timeout=cfg.timeout,
            )
        raise ValueError(f"Unsupported SMS driver: {entry.driver!r}")

    def _create_push(self, entry: NamedPushConfig) -> Any:
        """Instantiate the correct push implementation for a config."""
        if entry.driver == "fcm":
            if FCMPush is None:
                raise ImportError("FCMPush unavailable")
            fcm_cfg = entry.fcm or FCMDriverConfig()
            key = getattr(
                fcm_cfg.server_key, "get_secret_value", lambda: fcm_cfg.server_key or ""
            )()
            return FCMPush(server_key=key or "", timeout=fcm_cfg.timeout)
        if entry.driver == "apns":
            if APNsPush is None:
                raise ImportError(
                    "APNsPush unavailable — install lexigram-notification[apns]"
                )
            apns_cfg = entry.apns or APNsDriverConfig()
            return APNsPush(
                team_id=apns_cfg.team_id or "",
                key_id=apns_cfg.key_id or "",
                apns_auth_key=apns_cfg.apns_auth_key or "",
                bundle_id=apns_cfg.bundle_id or "",
                sandbox=apns_cfg.sandbox,
                timeout=apns_cfg.timeout,
            )
        if entry.driver == "web_push":
            if WebPushChannel is None:
                raise ImportError(
                    "WebPushChannel unavailable — install lexigram-notification[web-push]"
                )
            wp_cfg = entry.web_push or WebPushDriverConfig()
            return WebPushChannel(
                vapid_private_key=getattr(
                    wp_cfg.vapid_private_key,
                    "get_secret_value",
                    lambda: wp_cfg.vapid_private_key,  # type: ignore[arg-type]
                )(),
                vapid_public_key=wp_cfg.vapid_public_key or "",
                vapid_claims_subject=wp_cfg.vapid_claims_subject or "",
                http_timeout=wp_cfg.timeout,
            )
        raise ValueError(f"Unsupported push driver: {entry.driver!r}")

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Bind all SMS and push backends into the container."""
        self._config = self._requested_config or (
            self.config
            if isinstance(getattr(self, "config", None), NotificationConfig)
            else self._config
        )
        container.singleton(NotificationConfig, self._config)

        for entry in self._config.sms_backends:
            backend = self._create_sms(entry)
            self._sms_services.append((entry.name, backend))
            container.singleton(
                SMSChannelProtocol,
                factory=lambda *_, b=backend: b,
                name=entry.name,
            )
            is_primary = entry.primary or (
                not any(e.primary for e in self._config.sms_backends)
                and self._config.sms_backends[0] is entry
            )
            if is_primary:
                container.singleton(SMSChannelProtocol, factory=lambda *_, b=backend: b)

        for entry in self._config.push_backends:
            backend = self._create_push(entry)
            self._push_services.append((entry.name, backend))
            container.singleton(
                PushChannelProtocol,
                factory=lambda *_, b=backend: b,
                name=entry.name,
            )
            is_primary = entry.primary or (
                not any(e.primary for e in self._config.push_backends)
                and self._config.push_backends[0] is entry
            )
            if is_primary:
                container.singleton(PushChannelProtocol, factory=lambda *_, b=backend: b)

        logger.info(
            "notification_registered",
            sms=[n for n, _ in self._sms_services],
            push=[n for n, _ in self._push_services],
        )

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Health-check all backends; log warnings for degraded ones."""
        all_services = self._sms_services + self._push_services
        if not all_services:
            return
        results = await asyncio.gather(
            *[svc.health_check() for _, svc in all_services],
            return_exceptions=True,
        )
        for (name, _), result in zip(all_services, results, strict=True):
            if isinstance(result, Exception):
                logger.warning(
                    "notification_boot_unhealthy", backend=name, error=str(result)
                )

    async def shutdown(self) -> None:
        """Shutdown in reverse registration order."""
        for name, _ in reversed(self._push_services + self._sms_services):
            logger.info("notification_shutdown", backend=name)
        self._sms_services.clear()
        self._push_services.clear()

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Aggregate health across all registered notification backends."""
        all_services = self._sms_services + self._push_services
        if not all_services:
            return HealthCheckResult(
                component="notification",
                status=HealthStatus.HEALTHY,
                details={"backends": []},
            )

        results = await asyncio.gather(
            *[svc.health_check() for _, svc in all_services],
            return_exceptions=True,
        )
        worst = HealthStatus.HEALTHY
        details: dict[str, Any] = {}
        for (name, _), result in zip(all_services, results, strict=True):
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
            component="notification", status=worst, details=details
        )


__all__ = ["NotificationProvider"]

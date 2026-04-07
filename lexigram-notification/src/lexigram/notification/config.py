"""NotificationConfig following the config-system standard."""

from __future__ import annotations

from dataclasses import dataclass
from typing import ClassVar

from lexigram.config.base import BaseConfig
from lexigram.domain import DomainModel
from lexigram.notification.constants import (
    DEFAULT_APNS_TIMEOUT,
    DEFAULT_FCM_TIMEOUT,
    DEFAULT_SENDGRID_TIMEOUT,
    DEFAULT_SMTP_PORT,
    DEFAULT_SMTP_TIMEOUT,
    DEFAULT_TWILIO_TIMEOUT,
    ENV_NESTED_DELIMITER,
    ENV_PREFIX,
)
from lexigram.validation import ConfigDict, Field


@dataclass(init=False)
class TwilioDriverConfig(DomainModel):
    """Twilio SMS delivery configuration."""

    account_sid: str | None = Field(
        default=None,
        description="Twilio Account SID",
    )
    auth_token: str | None = Field(
        default=None,
        description="Twilio Auth Token",
    )
    from_number: str | None = Field(
        default=None,
        description="Twilio phone number (E.164 format)",
    )
    timeout: int = Field(
        default=DEFAULT_TWILIO_TIMEOUT,
        ge=1,
        description="HTTP timeout (s)",
    )


@dataclass(init=False)
class FCMDriverConfig(DomainModel):
    """Firebase Cloud Messaging (FCM) push notification configuration."""

    server_key: str | None = Field(
        default=None,
        description="FCM Server API Key",
    )
    timeout: int = Field(
        default=DEFAULT_FCM_TIMEOUT,
        ge=1,
        description="HTTP timeout (s)",
    )


@dataclass(init=False)
class APNsDriverConfig(DomainModel):
    """Apple Push Notification service (APNs) configuration."""

    team_id: str | None = Field(
        default=None,
        description="Apple Developer Team ID (10-character string)",
    )
    key_id: str | None = Field(
        default=None,
        description="APNs Auth Key ID (10-character string)",
    )
    apns_auth_key: str | None = Field(
        default=None,
        description=(
            "ECDSA private key — PEM string starting with "
            "'-----BEGIN PRIVATE KEY-----' or path to a .p8 key file"
        ),
    )
    bundle_id: str | None = Field(
        default=None,
        description="App bundle identifier (e.g. com.example.MyApp)",
    )
    sandbox: bool = Field(
        default=False,
        description="Use the APNs sandbox endpoint instead of production",
    )
    timeout: int = Field(
        default=DEFAULT_APNS_TIMEOUT,
        ge=1,
        description="HTTP timeout (s)",
    )


@dataclass(init=False)
class WebPushDriverConfig(DomainModel):
    """Web Push (RFC 8030) driver configuration."""

    vapid_private_key: str | None = Field(
        default=None,
        description="VAPID private key (PEM-encoded EC prime256v1)",
    )
    vapid_public_key: str | None = Field(
        default=None,
        description="VAPID public key (base64url-encoded)",
    )
    vapid_claims_subject: str | None = Field(
        default=None,
        description="VAPID claims subject URI (e.g. mailto:ops@example.com)",
    )
    timeout: int = Field(
        default=30,
        ge=1,
        description="HTTP timeout (s)",
    )


@dataclass(init=False)
class NamedSMSConfig(DomainModel):
    """Configuration for a single named SMS backend.

    Used in NotificationConfig.sms_backends to declare multiple SMS backends
    that the framework registers as named DI bindings.

    Example:
        sms_backends:
          - name: alerts
            driver: twilio
            primary: true
            twilio:
              account_sid: AC...
              auth_token: ...
              from_number: +1234567890

    Args:
        name: Unique backend identifier. Used as the Named() DI key.
        primary: Whether this is the primary backend. Primary backends
            also receive the unnamed SMSChannelProtocol binding.
        driver: SMS driver. One of 'twilio' or other supported drivers.
        twilio: Twilio-specific config.
    """

    name: str = Field(..., description="Unique backend name used as the Named() DI key")
    primary: bool = Field(
        default=False,
        description="Also register under unnamed SMSChannelProtocol binding",
    )
    driver: str = Field(default="twilio", description="SMS driver name")
    twilio: TwilioDriverConfig | None = Field(
        default=None,
        description="Twilio driver config",
    )


@dataclass(init=False)
class NamedPushConfig(DomainModel):
    """Configuration for a single named push notification backend.

    Used in NotificationConfig.push_backends to declare multiple push backends
    that the framework registers as named DI bindings.

    Example:
        push_backends:
          - name: mobile
            driver: fcm
            primary: true
            fcm:
              server_key: AAAA...

    Args:
        name: Unique backend identifier. Used as the Named() DI key.
        primary: Whether this is the primary backend. Primary backends
            also receive the unnamed PushChannelProtocol binding.
        driver: Push driver. One of 'fcm' or other supported drivers.
        fcm: FCM-specific config.
    """

    name: str = Field(..., description="Unique backend name used as the Named() DI key")
    primary: bool = Field(
        default=False,
        description="Also register under unnamed PushChannelProtocol binding",
    )
    driver: str = Field(default="fcm", description="Push driver name")
    fcm: FCMDriverConfig | None = Field(
        default=None,
        description="FCM driver config",
    )
    apns: APNsDriverConfig | None = Field(
        default=None,
        description="APNs driver config",
    )
    web_push: WebPushDriverConfig | None = Field(
        default=None,
        description="Web Push driver config",
    )


@dataclass(init=False)
class NotificationConfig(BaseConfig):
    """Top-level notification configuration.

    Loaded from the ``notification:`` key in application.yaml, with environment
    variable overrides via ``LEX_NOTIFICATION__*`` prefix.
    """

    config_section: ClassVar[str] = "notification"

    model_config: ClassVar[ConfigDict] = ConfigDict(  # type: ignore[typeddict-unknown-key]
        env_prefix=ENV_PREFIX,
        env_nested_delimiter=ENV_NESTED_DELIMITER,
        extra="ignore",
    )

    sms_backends: list[NamedSMSConfig] = Field(
        default_factory=list,
        description=(
            "Named SMS backends for multi-backend support. "
            "When non-empty, the provider registers each backend under "
            "Annotated[SMSChannelProtocol, Named(entry.name)]. "
            "The first entry (or the one with primary=True) also receives "
            "the unnamed SMSChannelProtocol binding for backward compatibility."
        ),
    )
    push_backends: list[NamedPushConfig] = Field(
        default_factory=list,
        description=(
            "Named push notification backends for multi-backend support. "
            "When non-empty, the provider registers each backend under "
            "Annotated[PushChannelProtocol, Named(entry.name)]. "
            "The first entry (or the one with primary=True) also receives "
            "the unnamed PushChannelProtocol binding for backward compatibility."
        ),
    )

    @classmethod
    def from_named_sms(cls, entry: NamedSMSConfig) -> NotificationConfig:
        """Build a single-SMS-backend NotificationConfig from a NamedSMSConfig entry.

        Used internally by NotificationProvider to create per-backend configs
        from a multi-backend declaration.

        Args:
            entry: The named SMS backend entry to materialise.

        Returns:
            A NotificationConfig configured for the single named SMS backend.
        """
        return cls(sms_backends=[entry])

    @classmethod
    def from_named_push(cls, entry: NamedPushConfig) -> NotificationConfig:
        """Build a single-push-backend NotificationConfig from a NamedPushConfig entry.

        Used internally by NotificationProvider to create per-backend configs
        from a multi-backend declaration.

        Args:
            entry: The named push backend entry to materialise.

        Returns:
            A NotificationConfig configured for the single named push backend.
        """
        return cls(push_backends=[entry])


# === Mailer Config (merged from mail/config.py) ===


@dataclass(init=False)
class SMTPDriverConfig(DomainModel):
    """SMTP-specific connection configuration."""

    host: str = Field(
        default="localhost",
        description="SMTP server hostname",
    )
    port: int = Field(
        default=DEFAULT_SMTP_PORT,
        ge=1,
        le=65535,
        description="SMTP port",
    )
    username: str | None = Field(
        default=None,
        description="SMTP auth username",
    )
    password: str | None = Field(
        default=None,
        description="SMTP auth password",
    )
    use_tls: bool = Field(
        default=True,
        description="Use STARTTLS (port 587)",
    )
    use_ssl: bool = Field(
        default=False,
        description="Use SSL from connect (port 465)",
    )
    timeout: int = Field(
        default=DEFAULT_SMTP_TIMEOUT,
        ge=1,
        description="Connection timeout (s)",
    )


@dataclass(init=False)
class SendGridDriverConfig(DomainModel):
    """SendGrid API configuration."""

    api_key: str | None = Field(
        default=None,
        description="SendGrid API key",
    )
    timeout: int = Field(
        default=DEFAULT_SENDGRID_TIMEOUT,
        ge=1,
        description="HTTP timeout (s)",
    )
    sandbox_mode: bool = Field(
        default=False,
        description="Sandbox mode — emails not sent",
    )


@dataclass(init=False)
class NamedMailerConfig(DomainModel):
    """Configuration for a single named mailer backend.

    Used in MailerConfig.backends to declare multiple mailer backends
    that the framework registers as named DI bindings.

    Example:
        backends:
          - name: transactional
            driver: sendgrid
            primary: true
            sendgrid:
              api_key: sg_...
          - name: internal
            driver: smtp
            smtp:
              host: smtp.example.com
              port: 587

    Args:
        name: Unique backend identifier. Used as the Named() DI key.
        primary: Whether this is the primary backend. Primary backends
            also receive the unnamed MailerProtocol binding.
        driver: Mailer driver. One of 'smtp' or 'sendgrid'.
        from_email: Default sender email address.
        from_name: Default sender display name.
        smtp: SMTP-specific connection config.
        sendgrid: SendGrid-specific config.
    """

    name: str = Field(..., description="Unique backend name used as the Named() DI key")
    primary: bool = Field(
        default=False,
        description="Also register under unnamed MailerProtocol binding",
    )
    driver: str = Field(default="smtp", description="Mailer driver name")
    from_email: str | None = Field(
        default=None,
        description="Default sender email address",
    )
    from_name: str | None = Field(
        default=None,
        description="Default sender display name",
    )
    smtp: SMTPDriverConfig | None = Field(
        default=None,
        description="SMTP driver config",
    )
    sendgrid: SendGridDriverConfig | None = Field(
        default=None,
        description="SendGrid driver config",
    )


@dataclass(init=False)
class MailerConfig(BaseConfig):
    """Top-level mailer configuration.

    Loaded from the ``mailer:`` key in application.yaml, with environment
    variable overrides via ``LEX_NOTIFICATION__MAILER__*`` prefix.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(  # type: ignore[typeddict-unknown-key]
        env_prefix="LEX_NOTIFICATION__MAILER__",
        env_nested_delimiter="__",
        extra="ignore",
    )

    backends: list[NamedMailerConfig] = Field(
        default_factory=list,
        description=(
            "Named mailer backends for multi-backend support. "
            "When non-empty, the provider registers each backend under "
            "Annotated[MailerProtocol, Named(entry.name)]. "
            "The first entry (or the one with primary=True) also receives "
            "the unnamed MailerProtocol binding for backward compatibility."
        ),
    )

    @classmethod
    def from_named(cls, entry: NamedMailerConfig) -> MailerConfig:
        """Build a single-backend MailerConfig from a NamedMailerConfig entry.

        Used internally by MailerProvider to create per-backend configs
        from a multi-backend declaration.

        Args:
            entry: The named backend entry to materialise.

        Returns:
            A MailerConfig configured for the single named backend.
        """
        return cls(backends=[entry])


# === Inbox Config (merged from inbox/config.py) ===

_INBOX_ENV_PREFIX = "LEX_NOTIFICATION__INBOX__"
_INBOX_ENV_NESTED_DELIMITER = "__"


@dataclass(init=False)
class InboxConfig(BaseConfig):
    """Top-level inbox configuration.

    Loaded from the ``inbox:`` key in application.yaml, with environment
    variable overrides via ``LEX_NOTIFICATION__INBOX__*`` prefix.

    Attributes:
        store_backend: Storage backend to use. One of ``'database'`` or
            ``'memory'``. Defaults to ``'database'``.
        max_page_size: Maximum number of messages returned per page.
        retention_days: Number of days to retain inbox messages before
            they are eligible for pruning.
        mark_read_on_fetch: When ``True`` messages are automatically marked
            as read when fetched via :meth:`~InboxService.get_inbox`.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(  # type: ignore[typeddict-unknown-key]
        env_prefix=_INBOX_ENV_PREFIX,
        env_nested_delimiter=_INBOX_ENV_NESTED_DELIMITER,
        extra="ignore",
    )

    store_backend: str = Field(
        default="database",
        description="Storage backend. One of 'database' or 'memory'.",
    )
    max_page_size: int = Field(
        default=50,
        ge=1,
        description="Maximum messages returned per page.",
    )
    retention_days: int = Field(
        default=30,
        ge=1,
        description="Days to retain inbox messages before pruning.",
    )
    mark_read_on_fetch: bool = Field(
        default=False,
        description="Automatically mark messages as read when fetched.",
    )


__all__ = [
    "APNsDriverConfig",
    "FCMDriverConfig",
    "InboxConfig",
    "MailerConfig",
    "NamedMailerConfig",
    "NamedPushConfig",
    "NamedSMSConfig",
    "NotificationConfig",
    "SMTPDriverConfig",
    "SendGridDriverConfig",
    "TwilioDriverConfig",
    "WebPushDriverConfig",
]

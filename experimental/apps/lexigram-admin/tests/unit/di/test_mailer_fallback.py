"""Debug-mode console mailer fallback registration tests (R11, doc 07)."""

from __future__ import annotations

from typing import Any

from lexigram.admin.config import AdminConfig
from lexigram.admin.di.sub_providers.auth_registrations import (
    register_new_auth_services,
)
from lexigram.admin.services.notifications.console_mailer import AdminConsoleMailer
from lexigram.contracts.mailer.protocols import MailerProtocol


class _RecordingContainer:
    """Registrar double: records singletons, answers ``has`` from them."""

    def __init__(self, prebound: dict | None = None) -> None:
        self.registered: dict[Any, Any] = dict(prebound or {})

    def singleton(self, key: Any, value: Any = None) -> None:
        self.registered[key] = value

    def has(self, key: Any) -> bool:
        return key in self.registered


def _config(debug: bool) -> AdminConfig:
    return AdminConfig.from_dict(
        {
            "debug": debug,
            "auth": {"session_secret": "unit-test-session-secret-value"},
        }
    )


class TestConsoleMailerFallback:
    def test_debug_without_mailer_registers_fallback(self) -> None:
        container = _RecordingContainer()
        register_new_auth_services(container, _config(debug=True))
        assert MailerProtocol in container.registered
        assert isinstance(container.registered[MailerProtocol], AdminConsoleMailer)

    def test_non_debug_never_registers_fallback(self) -> None:
        """Production stays explicit — no silent mail-swallowing backend."""
        container = _RecordingContainer()
        register_new_auth_services(container, _config(debug=False))
        assert MailerProtocol not in container.registered

    def test_existing_backend_is_never_overridden(self) -> None:
        sentinel = object()
        container = _RecordingContainer(prebound={MailerProtocol: sentinel})
        register_new_auth_services(container, _config(debug=True))
        assert container.registered[MailerProtocol] is sentinel

"""Optional external error tracking integration (Sentry).

Error tracking is gated entirely by :attr:`ErrorTrackingConfig.dsn` (env:
``LEX_MONITOR__ERROR_TRACKING__DSN``).  When no DSN is configured a
:class:`NullErrorTracker` is returned and the integration is a no-op.  When a
DSN is configured but ``sentry-sdk`` is not installed, setup degrades to the
no-op tracker with a warning instead of raising.

Example:
    ```python
    from lexigram.monitor.config import ErrorTrackingConfig
    from lexigram.monitor.error_tracking import setup_error_tracking

    tracker = setup_error_tracking(ErrorTrackingConfig(dsn="https://key@sentry.io/1"))
    try:
        ...
    except Exception as exc:
        tracker.capture_exception(exc)
    tracker.flush()
    ```
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable

from lexigram.logging import get_logger
from lexigram.monitor.config import ErrorTrackingConfig

logger = get_logger(__name__)


@runtime_checkable
class ErrorTrackerProtocol(Protocol):
    """Minimal interface for capturing exceptions to an external service."""

    def capture_exception(self, exc: BaseException) -> None:
        """Report an exception to the external error tracking service."""

    def flush(self, timeout: float = 2.0) -> None:
        """Flush buffered events to the external service.

        Args:
            timeout: Max seconds to wait for delivery.
        """


class NullErrorTracker:
    """No-op tracker used when no DSN is configured.

    Keeps capture/flush calls safe so callers never need to branch on
    whether error tracking is active.
    """

    def capture_exception(self, exc: BaseException) -> None:
        """Log the exception locally instead of reporting it externally."""
        logger.debug("error_tracking_noop", error=str(exc))

    def flush(self, timeout: float = 2.0) -> None:
        """Nothing to flush."""


class SentryErrorTracker:
    """Sentry-backed tracker used when a DSN is configured."""

    def __init__(self, config: ErrorTrackingConfig, sentry: Any) -> None:
        """Initialize the Sentry SDK.

        Args:
            config: Error tracking config with a non-empty ``dsn``.
            sentry: Imported ``sentry_sdk`` module.
        """
        self._config = config
        self._sentry = sentry
        sentry.init(
            dsn=config.dsn,
            environment=config.environment,
            traces_sample_rate=config.traces_sample_rate,
            send_default_pii=config.send_default_pii,
        )

    def capture_exception(self, exc: BaseException) -> None:
        """Report the exception to Sentry."""
        self._sentry.capture_exception(exc)

    def flush(self, timeout: float = 2.0) -> None:
        """Flush buffered events to Sentry.

        Args:
            timeout: Max seconds to wait for delivery.
        """
        self._sentry.flush(timeout=timeout)


def setup_error_tracking(config: ErrorTrackingConfig) -> ErrorTrackerProtocol:
    """Initialize error tracking from config; no-op when no DSN is set.

    Args:
        config: Error tracking configuration.  When ``dsn`` is unset or
            blank, a :class:`NullErrorTracker` is returned and no external
            connection is attempted.

    Returns:
        An active tracker when the DSN is set and ``sentry-sdk`` is
        installed, otherwise a no-op :class:`NullErrorTracker`.

    Example:
        ```python
        tracker = setup_error_tracking(MonitorConfig().error_tracking)
        ```
    """
    if not config.dsn or not config.dsn.strip():
        return NullErrorTracker()
    try:
        import sentry_sdk
    except ImportError:
        logger.warning(
            "error_tracking_skipped",
            reason="sentry-sdk is not installed",
            detail="Install sentry-sdk or lexigram-monitor extras to enable error tracking",
        )
        return NullErrorTracker()
    return SentryErrorTracker(config, sentry_sdk)


__all__ = [
    "ErrorTrackerProtocol",
    "NullErrorTracker",
    "SentryErrorTracker",
    "setup_error_tracking",
]

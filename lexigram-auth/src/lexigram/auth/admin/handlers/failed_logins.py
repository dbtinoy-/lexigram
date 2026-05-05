"""Failed logins widget handler."""

from __future__ import annotations

from lexigram.contracts.admin import Stat, StatContent, Tone, WidgetParams
from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.ai.session import SessionManagerProtocol
from lexigram.result import Ok, Result


class FailedLoginsWidgetHandler:
    """Handler for the failed logins widget.

    Args:
        session_manager: injected SessionManagerProtocol.
    """

    def __init__(self, session_manager: SessionManagerProtocol) -> None:
        """Initialize handler with session manager.

        Args:
            session_manager: SessionManagerProtocol for login failure tracking.
        """
        self._session_manager = session_manager

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch failed login statistics.

        Mirrors the widget template: a single ``is_elevated`` boundary gates
        the danger tone (the template's ``{% if is_elevated %}`` badge), with
        neutral styling otherwise. No multi-tier threshold ladder exists.

        Infrastructure failures propagate as exceptions.

        Args:
            params: Widget parameters (includes time_window_minutes).

        Returns:
            Result containing StatContent or AdminError.
        """
        # TODO: Implement failed login tracking
        # For now, return safe defaults (0, 0, False)
        count = 0
        unique_ips = 0
        is_elevated = False

        return Ok(
            self._build_content(
                count=count, unique_ips=unique_ips, is_elevated=is_elevated
            )
        )

    def _build_content(
        self, count: int, unique_ips: int, is_elevated: bool
    ) -> StatContent:
        """Build the StatContent mirroring the widget template.

        Args:
            count: Number of failed login attempts over the window.
            unique_ips: Number of unique source IPs.
            is_elevated: Whether the count is above the elevated threshold.

        Returns:
            StatContent with a danger tone when elevated and neutral styling
            otherwise, plus a conditional unique-IP stat.
        """
        tone = Tone.DANGER if is_elevated else Tone.PRIMARY
        stats: list[Stat] = [
            Stat(label="Failed Logins (1 hour)", value=str(count), tone=tone),
        ]
        if unique_ips > 0:
            stats.append(Stat(label="Unique IPs", value=str(unique_ips)))
        return StatContent(stats=tuple(stats))


__all__ = ["FailedLoginsWidgetHandler"]

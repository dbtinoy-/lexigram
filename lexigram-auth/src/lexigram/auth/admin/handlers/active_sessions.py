"""Active sessions widget handler."""

from __future__ import annotations

from lexigram.contracts.admin import Stat, StatContent, Tone, WidgetParams
from lexigram.contracts.admin.errors import AdminError
from lexigram.contracts.ai.session import SessionManagerProtocol
from lexigram.result import Ok, Result


class ActiveSessionsWidgetHandler:
    """Handler for the active sessions widget.

    Args:
        session_manager: injected SessionManagerProtocol.
    """

    def __init__(self, session_manager: SessionManagerProtocol) -> None:
        """Initialize handler with session manager.

        Args:
            session_manager: SessionManagerProtocol to retrieve active sessions.
        """
        self._session_manager = session_manager

    async def get_data(self, params: WidgetParams) -> Result[StatContent, AdminError]:
        """Fetch active sessions data.

        Mirrors the widget template: the count is rendered statically with
        neutral styling and the peak line is shown only when non-zero — no
        tone/threshold ladder exists in the template.

        Infrastructure failures propagate as exceptions.

        Args:
            params: Widget parameters (unused for this widget).

        Returns:
            Result containing StatContent or AdminError.
        """
        # TODO: Implement actual session statistics retrieval
        # For now, return safe defaults (0)
        count = 0
        peak_today = 0

        return Ok(self._build_content(count=count, peak_today=peak_today))

    def _build_content(self, count: int, peak_today: int) -> StatContent:
        """Build the StatContent mirroring the widget template.

        Args:
            count: Number of currently active sessions.
            peak_today: Peak session count today.

        Returns:
            StatContent with a static primary tone and a conditional peak stat.
        """
        stats: list[Stat] = [
            Stat(label="Currently Active", value=str(count), tone=Tone.PRIMARY),
        ]
        if peak_today > 0:
            stats.append(Stat(label="Peak today", value=str(peak_today)))
        return StatContent(stats=tuple(stats))


__all__ = ["ActiveSessionsWidgetHandler"]

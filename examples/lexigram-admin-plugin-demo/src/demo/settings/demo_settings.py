from __future__ import annotations

from lexigram.admin.pages.base import Page
from lexigram.admin.pages.types import PageResponse


class DemoSettingsPanel(Page):
    title = "Demo Settings"
    path = "/admin/demo/settings"

    async def view(self, request) -> PageResponse:
        return PageResponse(
            title=self.title,
            content=(
                "<div>"
                "<h2>Demo Settings</h2>"
                "<p>This panel demonstrates a settings page "
                "contributed by the demo plugin.</p>"
                "</div>"
            ),
        )

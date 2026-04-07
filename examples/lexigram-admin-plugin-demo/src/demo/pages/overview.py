from __future__ import annotations

from lexigram.admin.pages.base import Page
from lexigram.admin.pages.types import PageResponse


class OverviewPage(Page):
    title = "Plugin Overview"
    path = "/admin/demo/overview"

    async def view(self, request) -> PageResponse:
        return PageResponse(
            title=self.title,
            content=(
                "<div>"
                "<h2>Demo Plugin</h2>"
                "<p>This page demonstrates a custom management page "
                "contributed by the demo plugin.</p>"
                "</div>"
            ),
        )

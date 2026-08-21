"""AppLayout — the main UI shell for the Shorts Creator application."""

import math
import re

from lexigram.ui import BaseLayoutConfig, BaseLayoutContext, LayoutBase, el
from markupsafe import Markup


class AppLayout(LayoutBase):
    def __init__(self):
        config = BaseLayoutConfig(
            site_name="Shorts Creator",
            theme="system",
            htmx_enabled=True,
            htmx_version="2",
            htmx_boost=False,
            extra_head=(),
        )
        context = BaseLayoutContext(title="Shorts Creator — AI Video Studio")
        super().__init__(config=config, context=context)
        self.htmx_indicator = ""

    def render(self, content="", title=None, request=None, **extra_context):
        if request and request.headers.get("HX-Request") == "true":
            return Markup(content)
        return super().render(content=content, title=title, **extra_context)

    def render_body_content(self, content: str = "", **context) -> Any:
        """Render the main body content of the layout."""
        return el.div("", content, class_="")

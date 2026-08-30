"""Header actions (create).

Part of the ``lexigram.admin.actions.standard`` package.
"""

from __future__ import annotations

from typing import Any

from lexigram.admin.actions.base import HeaderAction
from lexigram.admin.actions.types import (
    ActionColor,
    ActionContext,
)
from lexigram.result import Ok, Result
from lexigram.ui import Zones


class CreateAction(HeaderAction):
    """Create a new record."""

    def __init__(
        self,
        name: str = "create",
        label: str | None = None,
    ) -> None:
        super().__init__(
            name=name,
            label=label or "Create",
            icon="plus",
            color=ActionColor.PRIMARY,
        )

    def _get_htmx_attrs(
        self, url: str, record: None, ctx: ActionContext
    ) -> dict[str, str]:
        mode = ctx.metadata.get("form_display_mode", "slider")
        if mode == "page":
            return {"href": url}
        zone = Zones.MODAL if mode == "modal" else Zones.SLIDE_OVER
        return {
            "hx-get": url,
            "hx-target": zone.selector,
            "hx-swap": zone.swap_mode.value,
            "hx-push-url": "false",
        }

    async def execute(self, record: None, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": "Created new record"})

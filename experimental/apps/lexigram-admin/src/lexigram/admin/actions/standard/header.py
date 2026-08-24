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
        return {
            "hx-get": url,
            "hx-target": Zones.SLIDE_OVER.selector,
            "hx-swap": Zones.SLIDE_OVER.swap_mode.value,
        }

    async def execute(self, record: None, ctx: ActionContext) -> Result[Any, Any]:
        return Ok({"message": "Created new record"})

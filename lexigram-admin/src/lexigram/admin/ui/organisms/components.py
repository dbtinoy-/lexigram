"""UI Organisms Components."""

from __future__ import annotations

from typing import Any

from lexigram.admin.config import TableConfiguration
from lexigram.admin.ui.organisms.command_palette import CommandPalette
from lexigram.admin.ui.organisms.data_table import DataTable
from lexigram.admin.ui.organisms.sidebar import Sidebar
from lexigram.ui import BulkAction, Column, Form, Repeater


def page_header(title, subtitle=None, actions=None) -> Any:
    """Create a page header with title, subtitle, and optional actions."""
    from lexigram.ui.core.base import el

    return el(
        "div",
        el(
            "div",
            el("h1", title, class_="text-2xl font-bold text-foreground"),
            el("p", subtitle, class_="mt-1 text-sm text-muted-foreground")
            if subtitle
            else "",
            class_="flex-1 min-w-0",
        ),
        el("div", actions, class_="mt-4 flex sm:mt-0 sm:ml-4") if actions else "",
        class_="mb-8 md:flex md:items-center md:justify-between",
    )


__all__ = [
    "BulkAction",
    "Column",
    "CommandPalette",
    "DataTable",
    "Form",
    "Repeater",
    "Sidebar",
    "TableConfiguration",
    "page_header",
]

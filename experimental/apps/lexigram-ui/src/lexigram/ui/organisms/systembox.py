from __future__ import annotations

from typing import Any

from lexigram.ui import Component, el


class SystemBox(Component):
    """
    A compact system menu display for the sidebar footer that mirrors the
    behavior of `UserBox`. It renders compact icons inline and exposes
    block-style items (e.g., Settings) in a dropdown for discoverability.
    """

    def __init__(
        self,
        system_menu_items: list[dict] | None = None,
        direction: str = "up",
        user: Any | None = None,
        **props: Any,
    ) -> None:
        super().__init__(
            system_menu_items=system_menu_items,
            direction=direction,
            user=user,
            **props,
        )
        self.system_menu_items = system_menu_items or []
        self.direction = direction
        self.user = user

    def render(self) -> Any:
        block_items = []
        compact_nodes = []

        # Old RBACChecker logic removed

        for m in self.system_menu_items:
            label = m.get("label") or ""
            href = m.get("href", "#")
            icon = m.get("icon")
            permission = m.get("permission")

            if permission and self.user:
                try:
                    # Check permission using AuthenticatedUserProtocol.has_permission
                    has_perm = False
                    if hasattr(self.user, "has_permission"):
                        has_perm = self.user.has_permission(permission)
                    elif hasattr(self.user, "permissions"):
                        # Basic check
                        has_perm = permission in self.user.permissions

                    if not has_perm:
                        # Skip guarded items when user lacks permission
                        continue
                except Exception as _perm_err:  # noqa: BLE001 — user permission objects may raise anything; conservative skip
                    from lexigram.logging import get_logger

                    logger = get_logger(__name__)
                    logger.exception(
                        "Error while evaluating permission '%s' for user", permission
                    )
                    # Conservative: skip if we can't evaluate permission
                    continue

            # Build content
            if icon:
                try:
                    from lexigram.ui import get_icon

                    content = get_icon(icon, class_name="w-5 h-5")
                except Exception as _icon_err:  # noqa: BLE001 — icon rendering is best-effort; fall back to plain text
                    from lexigram.logging import get_logger

                    logger = get_logger(__name__)
                    logger.exception("Failed to render icon '%s'", icon)
                    content = el("span", label)
            else:
                content = el(
                    "span",
                    label,
                    class_="text-sm text-foreground",
                )

            # Use any attributes supplied on the menu item (e.g., data-test hooks)
            attrs = dict(m.get("attrs", {}))

            # Block style (full-width) items are rendered in dropdown or as block anchors
            if m.get("render") == "block":
                # Create SidebarItem-like structure for block items
                first_letter = label[0] if label else ""

                # Check if icon is available for this item to optionally invoke it?
                # For now, just use label logic as icons are usually in 'compact_nodes' if intended for existing system box.
                # But 'Configuration' might have an icon in metadata?
                # If icon exists, we might want to hide it in mini mode like SidebarItem.

                # Icon (if present in metadata)
                icon_node = ""
                # Logic: If icon is present, show it always (adjust margin). Hide first letter.
                # If no icon, show first letter in mini mode.

                has_icon = False
                if icon:
                    has_icon = True
                    try:
                        from lexigram.ui import get_icon

                        # Icon Container: Show in both modes. Handle margin dynamically.
                        icon_node = el(
                            "div",
                            get_icon(icon, class_name="w-5 h-5"),
                            class_="transition-all duration-200",
                            **{"x-bind:class": "sidebarMini ? 'mr-0' : 'mr-3'"},
                        )
                    except (KeyError, ValueError):
                        pass

                first_letter_node = ""
                if not has_icon:
                    first_letter_node = el(
                        "span",
                        first_letter,
                        class_="font-bold text-xs w-6 h-6 flex items-center justify-center shrink-0 rounded-lg bg-muted dark:bg-card text-muted-foreground",
                        x_show="sidebarMini",
                    )

                block_link_attrs = {
                    "x-bind:class": "sidebarMini ? 'justify-center' : ''",
                    # Merge other attrs
                    **attrs,
                }
                if href and href != "#":
                    block_link_attrs["href"] = href
                block_items.append(
                    el(
                        "a" if href and href != "#" else "span",
                        icon_node,
                        # Full Label
                        el(
                            "span",
                            label,
                            class_="truncate whitespace-nowrap",
                            x_show="!sidebarMini",
                        ),
                        # Mini Label (First Letter)
                        first_letter_node,
                        class_=(
                            "group flex items-center px-3 py-2 rounded-xl text-sm font-medium transition-colors duration-200 text-muted-foreground dark:text-muted-foreground hover:bg-muted dark:hover:bg-card/50 hover:text-primary-600 dark:hover:text-primary-400"
                        ),
                        **block_link_attrs,
                    ),
                )
            else:
                compact_link_attrs = {
                    "title": label,
                    "class_": (
                        "inline-flex items-center justify-center p-2 rounded-md text-muted-foreground hover:bg-muted dark:text-foreground dark:hover:bg-card"
                    ),
                    **attrs,
                }
                if href and href != "#":
                    compact_link_attrs["href"] = href
                compact_nodes.append(
                    el(
                        "a" if href and href != "#" else "span",
                        content,
                        **compact_link_attrs,
                    ),
                )

        # Inline compact area
        compact_bar = (
            el("div", *compact_nodes, class_="flex items-center space-x-2")
            if compact_nodes
            else ""
        )

        # Render block items as a stacked list (flat, not popup)
        block_area = ""
        if block_items:
            block_area = el(
                "div",
                *block_items,
                class_="px-3 py-2 space-y-1",
            )

        # Place block items above compact icons to emulate stacked sidebar layout
        return el(
            "div",
            block_area,
            compact_bar,
            class_="flex flex-col px-3 py-2 border-b border-border",
        )

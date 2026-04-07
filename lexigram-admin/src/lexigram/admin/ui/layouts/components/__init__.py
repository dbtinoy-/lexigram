"""Layout components for lexigram-admin.

Reusable components used by various layouts.
"""

from __future__ import annotations

from lexigram.admin.ui.layouts.components.header import (
    HeaderConfig,
    HeaderRenderer,
    UserInfo,
)
from lexigram.admin.ui.layouts.components.sidebar import (
    NavGroup,
    NavItem,
    SidebarConfig,
    SidebarRenderer,
    build_nav_from_resources,
)
from lexigram.ui.layouts.footer import (
    FooterConfig,
    FooterLink,
    FooterRenderer,
)
from lexigram.ui.layouts.head import HeadConfig, HeadRenderer
from lexigram.ui.layouts.server_toasts import (
    ServerToastChannel,
    ToastConfig,
    ToastData,
    ToastType,
    flash_to_toast,
)

__all__ = [
    "FooterConfig",
    "FooterLink",
    # Footer
    "FooterRenderer",
    "HeadConfig",
    # Head
    "HeadRenderer",
    "HeaderConfig",
    # Header
    "HeaderRenderer",
    "NavGroup",
    "NavItem",
    "ServerToastChannel",
    "SidebarConfig",
    # Sidebar
    "SidebarRenderer",
    "ToastConfig",
    # Toasts
    "ToastData",
    "ToastType",
    "UserInfo",
    "build_nav_from_resources",
    "flash_to_toast",
]

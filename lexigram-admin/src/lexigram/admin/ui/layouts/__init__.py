"""Admin layouts for lexigram-admin.

This module provides layout components for the admin interface.

Layout hierarchy:
- HTMLDocument (abstract base)
  - BaseLayout (with mixins: CSS, JS, HTMX, Theme)
    - AdminLayout (full admin with sidebar)
    - StandaloneLayout (simple pages like login/error)
"""

from __future__ import annotations

# Admin layout
from lexigram.admin.ui.layouts.admin_layout import (
    AdminLayout,
    AdminLayoutConfig,
    AdminLayoutContext,
    NavItemConfig,
    admin_layout,
)

# Components
from lexigram.admin.ui.layouts.components import (
    FooterConfig,
    FooterLink,
    FooterRenderer,
    HeadConfig,
    HeaderConfig,
    HeaderRenderer,
    HeadRenderer,
    NavGroup,
    NavItem,
    ServerToastChannel,
    SidebarConfig,
    SidebarRenderer,
    ToastConfig,
    ToastData,
    ToastType,
    UserInfo,
    build_nav_from_resources,
    flash_to_toast,
)

# Standalone layout
from lexigram.admin.ui.layouts.standalone_layout import (
    StandaloneLayout,
    StandaloneLayoutConfig,
    StandaloneLayoutContext,
    standalone_layout,
)

# Tab group
from lexigram.admin.ui.layouts.tab_group import Tab, TabGroup

# Widgets
from lexigram.admin.ui.widgets import InfolistEntry, InfolistEntryType, InfolistWidget

# Base classes
from lexigram.ui.layouts import (
    BaseLayoutConfig,
    BaseLayoutContext,
    CSSManager,
    HTMLDocument,
    HTMLDocumentConfig,
    JSManager,
    LayoutBase,
)

__all__ = [  # noqa: RUF022
    "AdminLayout",
    "AdminLayoutConfig",
    "AdminLayoutContext",
    "LayoutBase",
    "BaseLayoutConfig",
    "BaseLayoutContext",
    "CSSManager",
    "FooterConfig",
    "FooterLink",
    # Components - Footer
    "FooterRenderer",
    # Base
    "HTMLDocument",
    "HTMLDocumentConfig",
    "InfolistEntry",
    "InfolistEntryType",
    "InfolistWidget",
    "JSManager",
    "HeadConfig",
    # Components - Head
    "HeadRenderer",
    "HeaderConfig",
    # Components - Header
    "HeaderRenderer",
    "NavGroup",
    "NavItem",
    "NavItemConfig",
    "SidebarConfig",
    # Components - Sidebar
    "SidebarRenderer",
    "StandaloneLayout",
    "StandaloneLayoutConfig",
    "StandaloneLayoutContext",
    "Tab",
    "TabGroup",
    "ServerToastChannel",
    "ToastConfig",
    # Components - Toast
    "ToastData",
    "ToastType",
    "UserInfo",
    # Admin layout
    "admin_layout",
    "build_nav_from_resources",
    "flash_to_toast",
    # Standalone layout
    "standalone_layout",
]

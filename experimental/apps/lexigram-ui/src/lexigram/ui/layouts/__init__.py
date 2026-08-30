"""General-purpose layout base classes and components for lexigram-ui.

Layout hierarchy:
- HTMLDocument (abstract base)
  - LayoutBase (with composition: CSSManager, JSManager, HTMX, Theme methods)
"""

from __future__ import annotations

from lexigram.ui.layouts.base_layout import (
    BaseLayoutConfig,
    BaseLayoutContext,
    LayoutBase,
)
from lexigram.ui.layouts.footer import (
    FooterConfig,
    FooterLink,
    FooterRenderer,
)
from lexigram.ui.layouts.head import HeadConfig, HeadRenderer
from lexigram.ui.layouts.html_document import (
    HTMLDocument,
    HTMLDocumentConfig,
)
from lexigram.ui.layouts.mixins import (
    CSSManager,
    JSManager,
)
from lexigram.ui.layouts.server_toasts import (
    ServerToastChannel,
    ToastConfig,
    ToastData,
    ToastType,
    flash_to_toast,
)

__all__ = [
    "BaseLayoutConfig",
    "BaseLayoutContext",
    "CSSManager",
    "FooterConfig",
    "FooterLink",
    "FooterRenderer",
    "HTMLDocument",
    "HTMLDocumentConfig",
    "HeadConfig",
    "HeadRenderer",
    "JSManager",
    "LayoutBase",
    "ServerToastChannel",
    "ToastConfig",
    "ToastData",
    "ToastType",
    "flash_to_toast",
]

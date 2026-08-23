"""Static layout re-exports for the ``lexigram.ui`` public surface.

Type-checker only: the top-level package resolves names lazily via
``__getattr__`` at runtime, so these imports never execute eagerly.
"""

# File-level suppression: this module is an intentional lazy-re-export
# manifest — imports live under TYPE_CHECKING on purpose.
# ruff: noqa: TC004


from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.ui.layouts import (
        BaseLayoutContext,
        CSSManager,
        HTMLDocument,
        JSManager,
        LayoutBase,
    )
    from lexigram.ui.layouts.footer import FooterLink, FooterRenderer
    from lexigram.ui.layouts.head import HeadRenderer

    __all__ = (
        "BaseLayoutContext",
        "CSSManager",
        "HTMLDocument",
        "JSManager",
        "LayoutBase",
        "FooterLink",
        "FooterRenderer",
        "HeadRenderer",
)

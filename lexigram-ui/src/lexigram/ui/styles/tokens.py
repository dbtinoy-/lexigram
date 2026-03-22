"""Semantic color maps for Lexigram UI components.

All values use CSS variable references (Tailwind arbitrary value syntax)
instead of hardcoded color classes. Tokens are resolved from ShadCN-
compatible CSS variables defined in design_tokens.py.
"""

from __future__ import annotations

SEMANTIC_CLASSES: dict[str, str] = {
    "default": "bg-muted text-muted-foreground",
    "gray": "bg-muted text-muted-foreground",
    "primary": "bg-primary text-primary-foreground",
    "success": "bg-success text-success-foreground dark:bg-success/20 dark:text-success",
    "warning": "bg-warning text-warning-foreground dark:bg-warning/20 dark:text-warning",
    "danger": "bg-destructive text-destructive-foreground dark:bg-destructive/25 dark:text-destructive",
    "error": "bg-destructive text-destructive-foreground dark:bg-destructive/25 dark:text-destructive",
    "info": "bg-info text-info-foreground dark:bg-info/20 dark:text-info",
    "red": "bg-destructive text-destructive-foreground dark:bg-destructive/25 dark:text-destructive",
    "yellow": "bg-warning text-warning-foreground dark:bg-warning/20 dark:text-warning",
    "green": "bg-success text-success-foreground dark:bg-success/20 dark:text-success",
    "blue": "bg-info text-info-foreground dark:bg-info/20 dark:text-info",
    "indigo": "bg-primary text-primary-foreground",
    "purple": "bg-primary text-primary-foreground",
    "pink": "bg-primary text-primary-foreground",
    "orange": "bg-warning text-warning-foreground dark:bg-warning/20 dark:text-warning",
}


SEMANTIC_ICONS: dict[str, str] = {
    "info": "info",
    "success": "check",
    "warning": "alert-circle",
    "error": "alert-circle",
    "danger": "alert-circle",
    "default": "info",
}

TOAST_CLASSES: dict[str, str] = {
    "info": "bg-info/20 text-info border border-info/30",
    "success": "bg-success/20 text-success border border-success/30",
    "warning": "bg-warning/20 text-warning border border-warning/30",
    "error": "bg-destructive/25 text-destructive border border-destructive/30",
    "danger": "bg-destructive/25 text-destructive border border-destructive/30",
    "default": "bg-primary text-primary-foreground",
}

ALERT_CLASSES: dict[str, str] = {
    "info": "bg-info/10 text-info border-info/30",
    "success": "bg-success/10 text-success border-success/30",
    "warning": "bg-warning/10 text-warning border-warning/30",
    "error": "bg-destructive/10 text-destructive border-destructive/30",
    "danger": "bg-destructive/10 text-destructive border-destructive/30",
}


def get_semantic_classes(variant: str, default: str = "default") -> str:
    """Resolve a variant name to CSS variable-based utility classes.

    Args:
        variant: Variant name (e.g. ``"success"``, ``"danger"``, ``"blue"``).
        default: Fallback when *variant* is not recognised.

    Returns:
        CSS class string for the resolved variant.
    """
    return SEMANTIC_CLASSES.get(variant, SEMANTIC_CLASSES[default])


def get_semantic_icon(variant: str, default: str = "info") -> str:
    """Resolve a variant name to a registered icon name.

    Args:
        variant: Variant name (e.g. ``"success"``, ``"error"``).
        default: Fallback when *variant* is not recognised.

    Returns:
        Icon name string (empty string if not found).
    """
    return SEMANTIC_ICONS.get(variant, SEMANTIC_ICONS.get(default, ""))


def get_toast_classes(toast_type: str, default: str = "default") -> str:
    """Resolve a toast type to CSS variable-based background classes.

    Args:
        toast_type: Toast type name (``"info"``, ``"success"``, etc.).
        default: Fallback when *toast_type* is not recognised.

    Returns:
        CSS class string for the resolved toast type.
    """
    return TOAST_CLASSES.get(toast_type, TOAST_CLASSES[default])


def get_alert_classes(variant: str, default: str = "info") -> str:
    """Resolve an alert variant to CSS variable-based alert classes.

    Args:
        variant: Alert variant (``"info"``, ``"success"``, etc.).
        default: Fallback when *variant* is not recognised.

    Returns:
        CSS class string for the resolved variant.
    """
    return ALERT_CLASSES.get(variant, ALERT_CLASSES[default])

from __future__ import annotations

from lexigram.ui.styles.tokens import (
    ALERT_CLASSES,
    SEMANTIC_CLASSES,
    SEMANTIC_ICONS,
    TOAST_CLASSES,
    get_alert_classes,
    get_semantic_classes,
    get_semantic_icon,
    get_toast_classes,
)


def test_get_semantic_classes_default() -> None:
    assert get_semantic_classes("default") == SEMANTIC_CLASSES["default"]
    assert "bg-muted" in SEMANTIC_CLASSES["default"]
    assert "text-muted-foreground" in SEMANTIC_CLASSES["default"]


def test_get_semantic_classes_primary() -> None:
    assert get_semantic_classes("primary") == SEMANTIC_CLASSES["primary"]
    assert "bg-primary" in SEMANTIC_CLASSES["primary"]
    assert "text-primary-foreground" in SEMANTIC_CLASSES["primary"]


def test_get_semantic_classes_fallback() -> None:
    assert get_semantic_classes("nonexistent") == SEMANTIC_CLASSES["default"]


def test_get_semantic_classes_all_variants_use_semantic_classes() -> None:
    for variant, classes in SEMANTIC_CLASSES.items():
        assert "bg-" in classes, f"{variant}: missing semantic background class"



def test_get_semantic_icon_known() -> None:
    assert get_semantic_icon("success") == "check"


def test_get_semantic_icon_fallback() -> None:
    assert get_semantic_icon("nonexistent") == SEMANTIC_ICONS["info"]


def test_get_toast_classes_known() -> None:
    assert get_toast_classes("success") == TOAST_CLASSES["success"]
    assert "bg-success" in TOAST_CLASSES["success"]


def test_get_toast_classes_fallback() -> None:
    assert get_toast_classes("nonexistent") == TOAST_CLASSES["default"]


def test_get_toast_classes_all_use_semantic_classes() -> None:
    for toast_type, classes in TOAST_CLASSES.items():
        assert "bg-" in classes, f"{toast_type}: missing semantic background class"


def test_get_alert_classes_known() -> None:
    assert get_alert_classes("info") == ALERT_CLASSES["info"]
    assert "bg-info" in ALERT_CLASSES["info"]


def test_get_alert_classes_fallback() -> None:
    assert get_alert_classes("nonexistent") == ALERT_CLASSES["info"]


def test_get_alert_classes_all_use_semantic_classes() -> None:
    for variant, classes in ALERT_CLASSES.items():
        assert "bg-" in classes, f"{variant}: missing semantic background class"


def test_semantic_icons_unchanged() -> None:
    assert SEMANTIC_ICONS == {
        "info": "info",
        "success": "check",
        "warning": "alert-circle",
        "error": "alert-circle",
        "danger": "alert-circle",
        "default": "info",
    }

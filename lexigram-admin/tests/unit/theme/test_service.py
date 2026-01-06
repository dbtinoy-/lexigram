from __future__ import annotations

from lexigram.admin.theme.service import AdminThemeService


def test_theme_service_defaults() -> None:
    service = AdminThemeService(primary_color="#6b7280")
    css = service.generate_theme_css()
    assert "--primary: #6b7280" in css


def test_theme_service_respects_config() -> None:
    service = AdminThemeService(primary_color="#3b82f6")
    css = service.generate_theme_css()
    assert "--primary: #3b82f6" in css


def test_theme_service_caches_css() -> None:
    service = AdminThemeService(primary_color="#6b7280")
    css1 = service.generate_theme_css()
    css2 = service.generate_theme_css()
    assert css1 is css2


def test_theme_service_invalidates_cache() -> None:
    service = AdminThemeService(primary_color="#6b7280")
    css1 = service.generate_theme_css()
    service.update_primary_color("#3b82f6")
    css2 = service.generate_theme_css()
    assert css1 is not css2
    assert "--primary: #3b82f6" in css2

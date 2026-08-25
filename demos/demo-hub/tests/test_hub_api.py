"""Tests for the demo hub registry, HTML rewriting, and API surface."""

from __future__ import annotations

import pytest

registry_mod = pytest.importorskip("demo_hub.services.registry")
subsite_mod = pytest.importorskip("demo_hub.subsite")


def test_registry_lists_all_thirteen_live_services() -> None:
    registry = registry_mod.ServiceRegistry()
    assert len(registry.web_services()) == 13


def test_registry_ports_are_unique_and_known() -> None:
    registry = registry_mod.ServiceRegistry()
    ports = [s.port for s in registry.services]
    assert len(set(ports)) == len(ports)
    assert 7000 not in ports  # the hub's own port


def test_every_web_demo_has_fleet_spec() -> None:
    for svc in registry_mod.ServiceRegistry().web_services():
        assert svc.demo_dir, svc.slug
        assert svc.app_path.endswith(".app"), svc.slug


def test_snapshot_reports_mounted_and_failed() -> None:
    reg = registry_mod.ServiceRegistry()
    snap = reg.snapshot(
        mounted={"resilient-rates": True},
        failures={"memory-chat": "Boom: x"},
    )
    by_slug = {s["slug"]: s["status"] for s in snap}
    assert by_slug["resilient-rates"] == "up"
    assert by_slug["memory-chat"] == "down"
    assert by_slug["llm-reproducibility"] == "cli"


def test_rewrite_html_prefixes_assets_and_injects_shim() -> None:
    html = b'<html><head><title>t</title></head><body><a href="/x">y</a></body></html>'
    out = subsite_mod.rewrite_html(html, "/demos/rates")
    assert b'href="/demos/rates/x"' in out
    assert b'var B="/demos/rates"' in out


def test_rewrite_js_rebases_location_navigation() -> None:
    js = b'if (x) { window.location.href = "/login"; }'
    out = subsite_mod.rewrite_js(js, "/demos/auth-rbac")
    assert b'window.location.href = "/demos/auth-rbac/login"' in out


def test_rewrite_js_leaves_fetch_and_comments_alone() -> None:
    js = b'fetch("/api/keys"); // location.href = "/keep"'
    out = subsite_mod.rewrite_js(js, "/demos/x")
    assert b'fetch("/api/keys")' in out


def test_rewrite_html_leaves_external_urls() -> None:
    html = (
        b'<html><head></head><body>'
        b'<a href="https://ex.com">e</a><a href="//cdn/x">p</a>'
        b"</body></html>"
    )
    out = subsite_mod.rewrite_html(html, "/demos/rates")
    assert b'"https://ex.com"' in out
    assert b'"//cdn/x"' in out

"""Validate every demo's UI serves correctly — pages, static assets, structure."""

from __future__ import annotations

import httpx
import pytest

registry_mod = pytest.importorskip("demo_hub.services.registry")


@pytest.fixture(scope="module")
def registry() -> registry_mod.ServiceRegistry:
    return registry_mod.ServiceRegistry()


@pytest.fixture(scope="module")
def client() -> httpx.Client:
    return httpx.Client(follow_redirects=True, timeout=10)


class TestDemoUIValidation:
    """Validate each demo's UI against its code."""

    def test_all_demos_return_200(self, registry: registry_mod.ServiceRegistry, client: httpx.Client) -> None:
        """Every web demo must serve its index page with HTTP 200."""
        for svc in registry.web_services():
            resp = client.get(f"http://127.0.0.1:7000/demos/{svc.slug}/")
            assert resp.status_code == 200, f"{svc.slug} returned {resp.status_code}"

    def test_all_demos_have_nav(self, registry: registry_mod.ServiceRegistry, client: httpx.Client) -> None:
        """Every demo must have a navigation bar."""
        for svc in registry.web_services():
            resp = client.get(f"http://127.0.0.1:7000/demos/{svc.slug}/")
            assert "<nav" in resp.text, f"{svc.slug} missing <nav>"

    def test_all_demos_have_brand(self, registry: registry_mod.ServiceRegistry, client: httpx.Client) -> None:
        """Every demo must have a nav-brand link."""
        for svc in registry.web_services():
            resp = client.get(f"http://127.0.0.1:7000/demos/{svc.slug}/")
            assert 'class="nav-brand"' in resp.text, f"{svc.slug} missing nav-brand"

    def test_all_demos_serve_css(self, registry: registry_mod.ServiceRegistry, client: httpx.Client) -> None:
        """Every demo must serve its stylesheet."""
        for svc in registry.web_services():
            resp = client.get(f"http://127.0.0.1:7000/demos/{svc.slug}/static/style.css")
            assert resp.status_code == 200, f"{svc.slug} CSS returned {resp.status_code}"
            assert "text/css" in resp.headers.get("content-type", ""), f"{svc.slug} CSS content-type wrong"

    def test_all_demos_serve_js(self, registry: registry_mod.ServiceRegistry, client: httpx.Client) -> None:
        """Every demo must serve its JavaScript (app.js or dashboard.js)."""
        for svc in registry.web_services():
            resp_app = client.get(f"http://127.0.0.1:7000/demos/{svc.slug}/static/app.js")
            resp_dash = client.get(f"http://127.0.0.1:7000/demos/{svc.slug}/static/dashboard.js")
            assert resp_app.status_code == 200 or resp_dash.status_code == 200, \
                f"{svc.slug} no JS found (app.js={resp_app.status_code}, dashboard.js={resp_dash.status_code})"

    def test_all_demos_serve_logo(self, registry: registry_mod.ServiceRegistry, client: httpx.Client) -> None:
        """Every demo must serve logo.png."""
        for svc in registry.web_services():
            resp = client.get(f"http://127.0.0.1:7000/demos/{svc.slug}/static/logo.png")
            assert resp.status_code == 200, f"{svc.slug} logo returned {resp.status_code}"

    def test_all_demos_serve_icon(self, registry: registry_mod.ServiceRegistry, client: httpx.Client) -> None:
        """Every demo must serve icon.png (favicon)."""
        for svc in registry.web_services():
            resp = client.get(f"http://127.0.0.1:7000/demos/{svc.slug}/static/icon.png")
            assert resp.status_code == 200, f"{svc.slug} icon returned {resp.status_code}"

    def test_all_demos_have_favicon_link(self, registry: registry_mod.ServiceRegistry, client: httpx.Client) -> None:
        """Every demo must have a favicon link tag."""
        for svc in registry.web_services():
            resp = client.get(f"http://127.0.0.1:7000/demos/{svc.slug}/")
            assert 'rel="icon"' in resp.text, f"{svc.slug} missing favicon link"

    def test_auth_demos_have_auth_shell(self, client: httpx.Client) -> None:
        """Auth demos must have the auth-shell container."""
        auth_slugs = ["auth-web", "auth-rbac", "auth-apikeys", "auth-mfa"]
        for slug in auth_slugs:
            resp = client.get(f"http://127.0.0.1:7000/demos/{slug}/")
            assert 'class="auth-shell"' in resp.text, f"{slug} missing auth-shell"
            assert 'class="auth-content"' in resp.text, f"{slug} missing auth-content"

    def test_auth_demos_have_card(self, client: httpx.Client) -> None:
        """Auth demos must have a card container."""
        auth_slugs = ["auth-web", "auth-rbac", "auth-apikeys", "auth-mfa"]
        for slug in auth_slugs:
            resp = client.get(f"http://127.0.0.1:7000/demos/{slug}/")
            assert 'class="card"' in resp.text, f"{slug} missing card"

    def test_hub_serves_all_demos(self, client: httpx.Client) -> None:
        """Hub must list all demos in its API."""
        resp = client.get("http://127.0.0.1:7000/api/status")
        assert resp.status_code == 200
        data = resp.json()
        slugs = {s["slug"] for s in data["services"]}
        registry = registry_mod.ServiceRegistry()
        expected = {s.slug for s in registry.web_services()}
        assert slugs == expected, f"Missing: {expected - slugs}, Extra: {slugs - expected}"

    def test_hub_serves_favicon(self, client: httpx.Client) -> None:
        """Hub must serve its own favicon."""
        resp = client.get("http://127.0.0.1:7000/static/icon.png")
        assert resp.status_code == 200

    def test_hub_has_group_filters(self, client: httpx.Client) -> None:
        """Hub must have Standard/Multi-module filter buttons."""
        resp = client.get("http://127.0.0.1:7000/")
        assert 'data-f="standard"' in resp.text
        assert 'data-f="multi-module"' in resp.text

    def test_demo_nav_css_identical(self, registry: registry_mod.ServiceRegistry, client: httpx.Client) -> None:
        """All demos must share identical nav CSS rules."""
        import re, hashlib

        nav_rules: dict[str, str] = {}
        for svc in registry.web_services():
            resp = client.get(f"http://127.0.0.1:7000/demos/{svc.slug}/static/style.css")
            rules = "\n".join(
                re.findall(r"(\.demo-nav[^{]*\{[^}]*\}|\.nav-[^{]*\{[^}]*\})", resp.text)
            )
            nav_rules[svc.slug] = rules

        hashes = {hashlib.md5(v.encode()).hexdigest() for v in nav_rules.values()}
        assert len(hashes) == 1, f"Nav CSS differs across demos: {hashes}"

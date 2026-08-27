"""Page controller tests for the auth-mfa demo."""

from __future__ import annotations

import httpx


async def test_login_renders(client: httpx.AsyncClient) -> None:
    r = await client.get("/login", follow_redirects=False)
    assert r.status_code == 200
    assert "Log in" in r.text


async def test_challenge_renders(client: httpx.AsyncClient) -> None:
    r = await client.get("/challenge", follow_redirects=False)
    assert r.status_code == 200
    assert "Two-factor" in r.text


async def test_profile_renders(client: httpx.AsyncClient) -> None:
    r = await client.get("/profile", follow_redirects=False)
    assert r.status_code == 200
    assert "Profile" in r.text


async def test_index_redirects(client: httpx.AsyncClient) -> None:
    r = await client.get("/", follow_redirects=False)
    assert r.status_code == 307


async def test_login_has_logo(client: httpx.AsyncClient) -> None:
    r = await client.get("/login", follow_redirects=False)
    assert "/static/logo.png" in r.text


async def test_challenge_has_logo(client: httpx.AsyncClient) -> None:
    r = await client.get("/challenge", follow_redirects=False)
    assert "/static/logo.png" in r.text


async def test_login_has_light_theme(client: httpx.AsyncClient) -> None:
    css = await client.get("/static/style.css")
    assert css.status_code == 200
    assert "#f8f9fa" in css.text


async def test_login_has_footer(client: httpx.AsyncClient) -> None:
    r = await client.get("/login", follow_redirects=False)
    assert "demo-footer" in r.text
    assert "lexigram.dev" in r.text


async def test_challenge_has_footer(client: httpx.AsyncClient) -> None:
    r = await client.get("/challenge", follow_redirects=False)
    assert "demo-footer" in r.text


async def test_css_returns(client: httpx.AsyncClient) -> None:
    r = await client.get("/static/style.css")
    assert r.status_code == 200


async def test_logo_returns_png(client: httpx.AsyncClient) -> None:
    r = await client.get("/static/logo.png")
    assert r.status_code == 200
    assert "image/png" in r.headers["content-type"]

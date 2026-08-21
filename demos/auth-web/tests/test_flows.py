"""End-to-end login/logout flow tests against the booted app."""

from __future__ import annotations

import httpx
import pytest
from starlette.applications import Starlette

from auth_web.di.provider import DEMO_EMAIL, DEMO_PASSWORD


async def login(client: httpx.AsyncClient) -> httpx.Response:
    return await client.post(
        "/login",
        data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
        follow_redirects=False,
    )


async def test_root_redirects_anonymous_to_login(client: httpx.AsyncClient) -> None:
    response = await client.get("/", follow_redirects=False)
    assert response.status_code in (302, 307)
    assert response.headers["location"] == "/login"


async def test_login_page_renders(client: httpx.AsyncClient) -> None:
    response = await client.get("/login")
    assert response.status_code == 200
    assert "Log in" in response.text


async def test_login_wrong_password_rerenders_with_error(
    client: httpx.AsyncClient,
) -> None:
    response = await client.post(
        "/login",
        data={"email": DEMO_EMAIL, "password": "wrong-password"},
    )
    assert response.status_code == 200
    assert "error" in response.text.lower()


async def test_login_success_sets_cookie_and_redirects(
    client: httpx.AsyncClient,
) -> None:
    response = await login(client)

    assert response.status_code in (302, 303, 307)
    assert response.headers["location"] == "/profile"
    assert "session_id" in response.cookies


async def test_logout_clears_cookie(client: httpx.AsyncClient) -> None:
    await login(client)

    response = await client.post("/logout", follow_redirects=False)

    assert response.status_code in (302, 303, 307)
    assert response.headers["location"] == "/login"


async def test_account_lockout_after_repeated_failures(
    client: httpx.AsyncClient,
) -> None:
    for _ in range(5):
        await client.post(
            "/login",
            data={"email": DEMO_EMAIL, "password": "wrong-password"},
        )
    response = await client.post(
        "/login",
        data={"email": DEMO_EMAIL, "password": DEMO_PASSWORD},
    )
    # Correct password must NOT bypass an active lockout.
    assert "locked" in response.text.lower()

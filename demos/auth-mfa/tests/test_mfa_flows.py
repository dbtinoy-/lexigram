"""End-to-end MFA flow tests: challenge, backup codes, enroll, disable."""

from __future__ import annotations

import httpx
import pytest
from starlette.applications import Starlette

from lexigram.auth.authn.mfa import generate_totp_code
from lexigram.auth.authn.user_service import UserService
from lexigram.auth.mfa.manager import MFAManager

PLAIN = {"email": "plain@mfa.demo", "password": "Demo-Password-1"}
MFA_USER = {"email": "mfa@mfa.demo", "password": "Demo-Password-1"}


def second_browser(app: Starlette) -> httpx.AsyncClient:
    """An independent browser (own cookie jar) over the same running app."""
    return httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    )


async def current_secret(app: Starlette, email: str) -> str:
    """Read the enrolled TOTP secret back out of the user's profile."""
    users = await app.container.resolve(UserService)
    user = await users.user_store.get_user_by_email(email)
    assert user is not None
    return user.profile["mfa"]["secret"]


async def code_for(app: Starlette, email: str) -> str:
    """Compute the current valid TOTP for a user."""
    secret = await current_secret(app, email)
    return generate_totp_code(secret)


async def login(client: httpx.AsyncClient, creds: dict[str, str]) -> httpx.Response:
    return await client.post("/api/login", json=creds)


async def test_plain_user_skips_challenge(client: httpx.AsyncClient) -> None:
    response = await login(client, PLAIN)

    assert response.status_code == 200
    assert response.json()["mfa_required"] is False
    assert "session_id" in response.cookies
    me = await client.get("/api/me")
    assert me.status_code == 200


async def test_mfa_login_issues_pending_challenge(client: httpx.AsyncClient) -> None:
    response = await login(client, MFA_USER)

    assert response.status_code == 200
    assert response.json()["mfa_required"] is True
    assert "mfa_pending" in response.cookies
    # No real session yet.
    me = await client.get("/api/me")
    assert me.status_code == 401


async def test_valid_code_upgrades_to_full_session(
    client: httpx.AsyncClient, app: Starlette
) -> None:
    await login(client, MFA_USER)
    code = await code_for(app, "mfa@mfa.demo")

    response = await client.post("/api/mfa/challenge", json={"code": code})

    assert response.status_code == 200
    assert "session_id" in response.cookies
    me = await client.get("/api/me")
    assert me.status_code == 200


async def test_wrong_code_attempts_are_capped(client: httpx.AsyncClient) -> None:
    await login(client, MFA_USER)

    statuses: list[tuple[int, str]] = []
    for _ in range(4):
        response = await client.post("/api/mfa/challenge", json={"code": "000000"})
        statuses.append((response.status_code, response.json().get("error", "")))

    assert all(status == 401 for status, _ in statuses)
    assert "too many attempts" in statuses[2][1]
    assert "no pending challenge" in statuses[3][1]


async def test_enroll_returns_provisioning_material_once(
    authed_plain: httpx.AsyncClient,
) -> None:
    response = await authed_plain.post("/api/mfa/enroll")

    assert response.status_code == 200
    body = response.json()
    assert body["provisioning_uri"].startswith("otpauth://totp/")
    assert len(body["backup_codes"]) >= 8


async def test_backup_code_works_exactly_once(
    client: httpx.AsyncClient, app: Starlette
) -> None:
    await client.post("/api/login", json=PLAIN)
    enroll = await client.post("/api/mfa/enroll")
    backup_code = enroll.json()["backup_codes"][0]

    async def challenge_with(browser: httpx.AsyncClient) -> httpx.Response:
        await browser.post("/api/login", json=MFA_PLAIN_LOGIN)
        return await browser.post("/api/mfa/challenge", json={"code": backup_code})

    first = second_browser(app)
    ok = await challenge_with(first)
    assert ok.status_code == 200

    second = second_browser(app)
    replay = await challenge_with(second)
    assert replay.status_code == 401
    await first.aclose()
    await second.aclose()


MFA_PLAIN_LOGIN = {"email": "plain@mfa.demo", "password": "Demo-Password-1"}


@pytest.fixture
async def authed_plain(
    app: Starlette, client: httpx.AsyncClient
) -> httpx.AsyncClient:
    await client.post("/api/login", json=PLAIN)
    return client


async def test_disable_requires_correct_password(
    authed_plain: httpx.AsyncClient,
) -> None:
    await authed_plain.post("/api/mfa/enroll")

    wrong = await authed_plain.post(
        "/api/mfa/disable", json={"password": "nope"}
    )
    assert wrong.status_code == 401

    status = await authed_plain.get("/api/mfa/status")
    assert status.json()["enabled"] is True

    right = await authed_plain.post(
        "/api/mfa/disable", json={"password": PLAIN["password"]}
    )
    assert right.status_code == 200
    status = await authed_plain.get("/api/mfa/status")
    assert status.json()["enabled"] is False

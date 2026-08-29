"""Web + Auth session scenario.

Packages under test: lexigram-web, lexigram-auth
Infrastructure: in-memory auth store (no live service)

Scenario:
1. Boot a minimal application with WebModule + AuthModule.
2. POST /api/v1/auth/register        -> 201 Created (new account)
3. POST /api/v1/auth/login           -> 200 OK, body contains access_token + refresh_token
4. GET  /api/v1/me (valid token)     -> 200 OK
5. GET  /api/v1/me (no token)        -> 401 Unauthorized
6. GET  /api/v1/me (expired token)   -> 401 Unauthorized
7. POST /api/v1/auth/refresh         -> 200 OK, fresh access_token
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

from tests.integration.scenarios._bed import scenario_bed
from tests.integration.scenarios.scenario_apps import create_web_auth_app

if TYPE_CHECKING:
    from tests.integration.scenarios._bed import ScenarioTestBed

pytestmark = [pytest.mark.integration, pytest.mark.scenario]


@pytest.fixture
async def bed() -> "ScenarioTestBed":
    """Boot a minimal Web + Auth test application."""
    async with scenario_bed(create_web_auth_app) as scenario:
        yield scenario


class TestWebAuthSession:
    """Web + Auth login, JWT issuance, and protected-route enforcement."""

    async def test_register_user(self, bed: "ScenarioTestBed") -> None:
        """Registering with valid credentials returns 201 and a user payload."""
        resp = await bed.client.post(
            "/api/v1/auth/register",
            json={"email": "alice@example.com", "password": "s3cur3P@ss"},
        )
        assert resp.status_code == 201
        assert resp.json()["email"] == "alice@example.com"

    async def test_login_returns_token(self, bed: "ScenarioTestBed") -> None:
        """Logging in with valid credentials returns access and refresh tokens."""
        await bed.client.post(
            "/api/v1/auth/register",
            json={"email": "bob@example.com", "password": "s3cur3P@ss"},
        )
        resp = await bed.client.post(
            "/api/v1/auth/login",
            json={"email": "bob@example.com", "password": "s3cur3P@ss"},
        )
        assert resp.status_code == 200
        body = resp.json()
        assert "access_token" in body
        assert "refresh_token" in body

    async def test_protected_route_with_valid_token(self, bed: "ScenarioTestBed") -> None:
        """A valid bearer token grants access to a protected route."""
        await bed.client.post(
            "/api/v1/auth/register",
            json={"email": "carol@example.com", "password": "s3cur3P@ss"},
        )
        login = await bed.client.post(
            "/api/v1/auth/login",
            json={"email": "carol@example.com", "password": "s3cur3P@ss"},
        )
        token = login.json()["access_token"]

        resp = await bed.client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {token}"},
        )
        assert resp.status_code == 200
        assert resp.json()["email"] == "carol@example.com"

    async def test_protected_route_without_token_returns_401(
        self, bed: "ScenarioTestBed"
    ) -> None:
        """Accessing a protected route without a token returns 401."""
        resp = await bed.client.get("/api/v1/me")
        assert resp.status_code == 401

    async def test_expired_token_returns_401(self, bed: "ScenarioTestBed") -> None:
        """Presenting an expired JWT to a protected route returns 401."""
        expired_token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiJ4IiwiZXhwIjoxfQ.sig"
        resp = await bed.client.get(
            "/api/v1/me",
            headers={"Authorization": f"Bearer {expired_token}"},
        )
        assert resp.status_code == 401

    async def test_token_refresh(self, bed: "ScenarioTestBed") -> None:
        """Posting a valid refresh token returns a fresh access token."""
        await bed.client.post(
            "/api/v1/auth/register",
            json={"email": "dave@example.com", "password": "s3cur3P@ss"},
        )
        login = await bed.client.post(
            "/api/v1/auth/login",
            json={"email": "dave@example.com", "password": "s3cur3P@ss"},
        )
        refresh_token = login.json()["refresh_token"]

        resp = await bed.client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert resp.status_code == 200
        assert "access_token" in resp.json()

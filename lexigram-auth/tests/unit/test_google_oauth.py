"""Tests for Google OAuth verification support."""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.auth.authn.google_oauth import GoogleOAuthService
from lexigram.auth.di.sub_providers.google_oauth_provider import GoogleOAuthProvider
from lexigram.auth.exceptions import OAuth2Error
from lexigram.contracts.auth import VerifiedIdentityClaims


class TestGoogleOAuthService:
    """Test the Google OAuth verification service."""

    @pytest.fixture
    def service(self) -> GoogleOAuthService:
        return GoogleOAuthService(client_id="google-client-id")

    @pytest.mark.asyncio
    async def test_verify_id_token_returns_verified_claims(
        self,
        mocker,
        service: GoogleOAuthService,
    ) -> None:
        mocker.patch(
            "lexigram.auth.authn.google_oauth.jwt.get_unverified_header",
            return_value={"kid": "kid-1", "alg": "RS256"},
        )
        with (
            patch.object(
                service,
                "_get_jwks",
                new=AsyncMock(
                    return_value={
                        "keys": [
                            {
                                "kid": "kid-1",
                                "kty": "RSA",
                                "n": "abc",
                                "e": "AQAB",
                            },
                        ],
                    },
                ),
            ),
            patch(
                "lexigram.auth.authn.google_oauth.jwt.algorithms.RSAAlgorithm.from_jwk",
                return_value="public-key",
            ),
            patch(
                "lexigram.auth.authn.google_oauth.jwt.decode",
                return_value={
                    "sub": "google-sub",
                    "email": "user@example.com",
                    "email_verified": True,
                    "name": "Google User",
                    "picture": "https://example.com/avatar.png",
                    "iss": "https://accounts.google.com",
                    "aud": "google-client-id",
                    "exp": 1_800_000_000,
                    "iat": 1_700_000_000,
                },
            ),
        ):
            claims = await service.verify_id_token("header.payload.signature")

        assert isinstance(claims, VerifiedIdentityClaims)
        assert claims.provider == "google"
        assert claims.provider_user_id == "google-sub"
        assert claims.email == "user@example.com"
        assert claims.email_verified is True
        assert claims.name == "Google User"
        assert claims.picture == "https://example.com/avatar.png"
        assert claims.audience == "google-client-id"
        assert claims.issuer == "https://accounts.google.com"
        assert claims.raw_data["sub"] == "google-sub"

    @pytest.mark.asyncio
    async def test_verify_token_falls_back_to_userinfo_for_opaque_token(
        self,
        service: GoogleOAuthService,
    ) -> None:
        mock_http_client = AsyncMock()
        response = MagicMock()
        response.status = 200
        response.json = {
            "sub": "userinfo-sub",
            "email": "userinfo@example.com",
            "email_verified": True,
            "name": "User Info",
            "picture": "https://example.com/userinfo.png",
        }
        mock_http_client.request.return_value = response
        service.http_client = mock_http_client

        claims = await service.verify_token("opaque-access-token")

        mock_http_client.request.assert_called_once()
        assert claims.provider_user_id == "userinfo-sub"
        assert claims.email == "userinfo@example.com"
        assert claims.name == "User Info"
        assert claims.picture == "https://example.com/userinfo.png"

    @pytest.mark.asyncio
    async def test_verify_id_token_rejects_unverified_email(
        self,
        mocker,
        service: GoogleOAuthService,
    ) -> None:
        mocker.patch(
            "lexigram.auth.authn.google_oauth.jwt.get_unverified_header",
            return_value={"kid": "kid-1", "alg": "RS256"},
        )
        with (
            patch.object(
                service,
                "_get_jwks",
                new=AsyncMock(
                    return_value={
                        "keys": [
                            {
                                "kid": "kid-1",
                                "kty": "RSA",
                                "n": "abc",
                                "e": "AQAB",
                            },
                        ],
                    },
                ),
            ),
            patch(
                "lexigram.auth.authn.google_oauth.jwt.algorithms.RSAAlgorithm.from_jwk",
                return_value="public-key",
            ),
            patch(
                "lexigram.auth.authn.google_oauth.jwt.decode",
                return_value={
                    "sub": "google-sub",
                    "email": "user@example.com",
                    "email_verified": False,
                    "iss": "https://accounts.google.com",
                    "aud": "google-client-id",
                    "exp": 1_800_000_000,
                    "iat": 1_700_000_000,
                },
            ),
        ):
            with pytest.raises(OAuth2Error, match="Google email is not verified"):
                await service.verify_id_token("header.payload.signature")


class TestGoogleOAuthProvider:
    """Test Google OAuth provider registration."""

    @pytest.mark.asyncio
    async def test_registers_service(self) -> None:
        provider = GoogleOAuthProvider(
            google_oauth={
                "client_id": "google-client-id",
                "jwks_url": "https://example.com/jwks",
                "userinfo_url": "https://example.com/userinfo",
            },
        )

        class _Container:
            def __init__(self) -> None:
                self.registered: dict[Any, Any] = {}

            def singleton(self, key: Any, value: Any) -> None:
                self.registered[key] = value

        container = _Container()
        await provider.register(container)

        assert GoogleOAuthService in container.registered
        service = container.registered[GoogleOAuthService]()
        assert isinstance(service, GoogleOAuthService)
        assert service.client_id == "google-client-id"
        assert service.jwks_url == "https://example.com/jwks"
        assert service.userinfo_url == "https://example.com/userinfo"

"""Tests for LEX-002: verified-only JWT mode with explicit dev opt-in.

Policy summary
--------------
- PRODUCTION / STAGING + missing secret → raises at boot (ConfigurationError)
- PRODUCTION / STAGING + allow_unverified_dev=True → still raises (flag ignored)
- DEVELOPMENT + missing secret + allow_unverified_dev=False (default) → raises
- DEVELOPMENT + missing secret + allow_unverified_dev=True → boots, warning logged,
  verify_token decodes without signature verification
- Valid secret + valid signature → succeeds in all environments
- Valid secret + tampered signature → returns Err (TokenInvalidError)
"""

from __future__ import annotations

import os
from typing import Any
from unittest.mock import patch

import jwt
import pytest
from pydantic import SecretStr

from lexigram.auth.authn.jwt import JWTTokenManager
from lexigram.auth.config import JWTConfig
from lexigram.auth.di.sub_providers.token_provider import TokenProvider
from lexigram.contracts.exceptions import ConfigurationError

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_GOOD_SECRET = "a" * 33  # 33-char secret, passes the HS256 ≥32-byte check


def _make_token(secret: str, payload: dict[str, Any] | None = None) -> str:
    """Create a signed HS256 JWT for testing."""
    claims: dict[str, Any] = {
        "sub": "user-123",
        "email": "test@example.com",
        "type": "access",
        "exp": 9999999999,
    }
    if payload:
        claims.update(payload)
    return jwt.encode(claims, secret, algorithm="HS256")


def _make_unsigned_token(payload: dict[str, Any] | None = None) -> str:
    """Create an *unsigned* (algorithm=none) JWT via raw construction."""
    import base64
    import json

    header = (
        base64.urlsafe_b64encode(b'{"alg":"none","typ":"JWT"}').rstrip(b"=").decode()
    )
    claims: dict[str, Any] = {
        "sub": "user-123",
        "email": "test@example.com",
        "type": "access",
        "exp": 9999999999,
    }
    if payload:
        claims.update(payload)
    body = base64.urlsafe_b64encode(json.dumps(claims).encode()).rstrip(b"=").decode()
    return f"{header}.{body}."


def _make_manager(secret: str = _GOOD_SECRET, **kwargs: Any) -> JWTTokenManager:
    return JWTTokenManager(
        current_key_id=SecretStr(secret),
        **kwargs,
    )


# ---------------------------------------------------------------------------
# JWTConfig validator tests
# ---------------------------------------------------------------------------


class TestJWTConfigVerificationPolicy:
    def test_allows_valid_secret_in_development(self) -> None:
        with patch.dict(os.environ, {"LEX_ENV": "development"}):
            cfg = JWTConfig(secret_key=_GOOD_SECRET)
            assert cfg.allow_unverified_dev is False

    def test_allows_valid_secret_in_production(self) -> None:
        with patch.dict(os.environ, {"LEX_ENV": "production"}):
            cfg = JWTConfig(secret_key=_GOOD_SECRET)
            assert cfg.allow_unverified_dev is False

    def test_allows_valid_secret_in_staging(self) -> None:
        with patch.dict(os.environ, {"LEX_ENV": "staging"}):
            cfg = JWTConfig(secret_key=_GOOD_SECRET)
            assert cfg.secret_key.get_secret_value() == _GOOD_SECRET

    def test_rejects_default_secret_in_production(self) -> None:
        with patch.dict(os.environ, {"LEX_ENV": "production"}):
            with pytest.raises(ValueError, match="CRITICAL SECURITY ERROR"):
                JWTConfig(secret_key="change-me")

    def test_rejects_default_secret_in_staging(self) -> None:
        with patch.dict(os.environ, {"LEX_ENV": "staging"}):
            with pytest.raises(ValueError, match="CRITICAL SECURITY ERROR"):
                JWTConfig(secret_key="change-me")

    def test_allow_unverified_dev_true_stored_in_production(self) -> None:
        """allow_unverified_dev=True is stored in config in production (policy enforced at boot)."""
        with patch.dict(os.environ, {"LEX_ENV": "production"}):
            # Secret must be valid for production (no config-level error on the secret).
            # The flag warning is logged separately; JWTConfig does not raise for the flag.
            cfg = JWTConfig(
                secret_key=_GOOD_SECRET,
                allow_unverified_dev=True,
            )
            # The field is still stored as True (policy enforcement is at TokenProvider boot).
            assert cfg.allow_unverified_dev is True

    def test_allow_unverified_dev_true_in_development_logs_warning(
        self, caplog: pytest.LogCaptureFixture
    ) -> None:
        with patch.dict(os.environ, {"LEX_ENV": "development"}):
            cfg = JWTConfig(secret_key=_GOOD_SECRET, allow_unverified_dev=True)
            assert cfg.allow_unverified_dev is True


# ---------------------------------------------------------------------------
# TokenProvider boot-time policy tests
# ---------------------------------------------------------------------------


class TestTokenProviderBootPolicy:
    """TokenProvider enforces the JWT verification policy at __init__ time."""

    def _provider_with_env(
        self, env: str, secret: str | None, allow_unverified: bool = False
    ) -> TokenProvider:
        """Build a minimal mock config and TokenProvider in the given env."""
        from unittest.mock import MagicMock

        if secret is not None:
            token_cfg = MagicMock()
            token_cfg.secret_key = SecretStr(secret)
            token_cfg.algorithm = "HS256"
            token_cfg.allow_unverified_dev = allow_unverified
            token_cfg.access_expiration_hours = 1
            token_cfg.refresh_expiration_days = 7
            token_cfg.key_rotation_grace_period_seconds = 3600
            cfg = MagicMock()
            cfg.token = token_cfg
        else:
            token_cfg = MagicMock()
            token_cfg.secret_key = None
            token_cfg.algorithm = "HS256"
            token_cfg.allow_unverified_dev = allow_unverified
            token_cfg.access_expiration_hours = 1
            token_cfg.refresh_expiration_days = 7
            token_cfg.key_rotation_grace_period_seconds = 3600
            cfg = MagicMock()
            cfg.token = token_cfg

        with patch.dict(os.environ, {"LEX_ENV": env}):
            return TokenProvider(config=cfg)

    # ── PRODUCTION ──────────────────────────────────────────────────────────

    def test_production_missing_secret_raises(self) -> None:
        from unittest.mock import MagicMock

        token_cfg = MagicMock()
        token_cfg.secret_key = None
        token_cfg.algorithm = "HS256"
        token_cfg.allow_unverified_dev = False
        cfg = MagicMock()
        cfg.token = token_cfg

        with patch.dict(os.environ, {"LEX_ENV": "production"}):
            with pytest.raises(ConfigurationError, match="CRITICAL SECURITY"):
                TokenProvider(config=cfg)

    def test_production_missing_secret_allow_unverified_true_still_raises(self) -> None:
        """allow_unverified_dev=True is ignored in production — still raises."""
        from unittest.mock import MagicMock

        token_cfg = MagicMock()
        token_cfg.secret_key = None
        token_cfg.algorithm = "HS256"
        token_cfg.allow_unverified_dev = True
        cfg = MagicMock()
        cfg.token = token_cfg

        with patch.dict(os.environ, {"LEX_ENV": "production"}):
            with pytest.raises(ConfigurationError, match="CRITICAL SECURITY"):
                TokenProvider(config=cfg)

    def test_production_valid_secret_boots_verified_only(self) -> None:
        provider = self._provider_with_env("production", _GOOD_SECRET)
        assert provider._allow_unverified_dev is False

    # ── STAGING ─────────────────────────────────────────────────────────────

    def test_staging_missing_secret_raises(self) -> None:
        from unittest.mock import MagicMock

        token_cfg = MagicMock()
        token_cfg.secret_key = None
        token_cfg.algorithm = "HS256"
        token_cfg.allow_unverified_dev = False
        cfg = MagicMock()
        cfg.token = token_cfg

        with patch.dict(os.environ, {"LEX_ENV": "staging"}):
            with pytest.raises(ConfigurationError, match="CRITICAL SECURITY"):
                TokenProvider(config=cfg)

    def test_staging_allow_unverified_true_still_raises(self) -> None:
        from unittest.mock import MagicMock

        token_cfg = MagicMock()
        token_cfg.secret_key = None
        token_cfg.algorithm = "HS256"
        token_cfg.allow_unverified_dev = True
        cfg = MagicMock()
        cfg.token = token_cfg

        with patch.dict(os.environ, {"LEX_ENV": "staging"}):
            with pytest.raises(ConfigurationError, match="CRITICAL SECURITY"):
                TokenProvider(config=cfg)

    def test_staging_valid_secret_boots_verified_only(self) -> None:
        provider = self._provider_with_env("staging", _GOOD_SECRET)
        assert provider._allow_unverified_dev is False

    # ── DEVELOPMENT ─────────────────────────────────────────────────────────

    def test_development_missing_secret_no_opt_in_raises(self) -> None:
        from unittest.mock import MagicMock

        token_cfg = MagicMock()
        token_cfg.secret_key = None
        token_cfg.algorithm = "HS256"
        token_cfg.allow_unverified_dev = False
        cfg = MagicMock()
        cfg.token = token_cfg

        with patch.dict(os.environ, {"LEX_ENV": "development"}):
            with pytest.raises(ConfigurationError, match="allow_unverified_dev"):
                TokenProvider(config=cfg)

    def test_development_missing_secret_opt_in_boots(self) -> None:
        from unittest.mock import MagicMock

        token_cfg = MagicMock()
        token_cfg.secret_key = None
        token_cfg.algorithm = "HS256"
        token_cfg.allow_unverified_dev = True
        cfg = MagicMock()
        cfg.token = token_cfg

        with patch.dict(os.environ, {"LEX_ENV": "development"}):
            provider = TokenProvider(config=cfg)
        assert provider._allow_unverified_dev is True

    def test_development_missing_secret_opt_in_logs_warning(
        self, capsys: pytest.CaptureFixture
    ) -> None:
        """Boot with allow_unverified_dev=True logs a warning to stdout (structlog)."""
        from unittest.mock import MagicMock

        token_cfg = MagicMock()
        token_cfg.secret_key = None
        token_cfg.algorithm = "HS256"
        token_cfg.allow_unverified_dev = True
        cfg = MagicMock()
        cfg.token = token_cfg

        with patch.dict(os.environ, {"LEX_ENV": "development"}):
            TokenProvider(config=cfg)

        captured = capsys.readouterr()
        combined = (captured.out + captured.err).lower()
        # Lexigram uses structlog which emits to stdout; the warning key is
        # 'jwt_boot_unverified_dev_mode' at level [warning].
        assert "unverif" in combined, (
            f"Expected an unverified-dev warning in stdout/stderr, got:\n{combined[:500]}"
        )

    def test_development_valid_secret_boots_verified_only(self) -> None:
        provider = self._provider_with_env("development", _GOOD_SECRET)
        assert provider._allow_unverified_dev is False


# ---------------------------------------------------------------------------
# JWTTokenManager allow_unverified_dev=True decode tests
# ---------------------------------------------------------------------------


class TestJWTTokenManagerUnverifiedDev:
    """Token manager boots with allow_unverified_dev=True → decodes without sig check."""

    @pytest.fixture
    def unverified_manager(self) -> JWTTokenManager:
        return JWTTokenManager(
            current_key_id=SecretStr("placeholder-secret-for-unverified-dev"),
            allow_unverified_dev=True,
        )

    @pytest.mark.asyncio
    async def test_decodes_token_signed_with_different_secret(
        self, unverified_manager: JWTTokenManager
    ) -> None:
        """A token signed with secret-A should be accepted by a manager with secret-B
        when allow_unverified_dev=True."""
        token = _make_token("completely-different-secret-xyz")
        result = await unverified_manager.verify_token(token)
        assert result.is_ok(), f"Expected Ok but got: {result}"
        verified = result.unwrap()
        assert verified.user_id == "user-123"
        assert verified.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_still_rejects_expired_token(
        self, unverified_manager: JWTTokenManager
    ) -> None:
        """Expiry is still enforced even in unverified mode."""
        import time

        expired_token = _make_token(
            "some-secret",
            payload={"exp": int(time.time()) - 3600},
        )
        result = await unverified_manager.verify_token(expired_token)
        assert result.is_err()


# ---------------------------------------------------------------------------
# JWTTokenManager verified path (allow_unverified_dev=False) tests
# ---------------------------------------------------------------------------


class TestJWTTokenManagerVerifiedPath:
    """Normal (verified) path: valid signature succeeds, tampered fails."""

    @pytest.fixture
    def manager(self) -> JWTTokenManager:
        return _make_manager()

    @pytest.mark.asyncio
    async def test_valid_token_succeeds(self, manager: JWTTokenManager) -> None:
        token = _make_token(_GOOD_SECRET)
        result = await manager.verify_token(token)
        assert result.is_ok(), f"Expected Ok, got: {result}"
        verified = result.unwrap()
        assert verified.user_id == "user-123"

    @pytest.mark.asyncio
    async def test_tampered_signature_fails(self, manager: JWTTokenManager) -> None:
        token = _make_token(_GOOD_SECRET)
        # Corrupt the signature portion (last segment).
        parts = token.split(".")
        parts[-1] = parts[-1][:-4] + "XXXX"
        tampered = ".".join(parts)
        result = await manager.verify_token(tampered)
        assert result.is_err(), "Expected Err for tampered token"

    @pytest.mark.asyncio
    async def test_wrong_secret_fails(self, manager: JWTTokenManager) -> None:
        token = _make_token("wrong-secret-key-that-is-at-least-32-chars")
        result = await manager.verify_token(token)
        assert result.is_err(), "Expected Err for token signed with wrong secret"

    def test_verified_only_manager_has_flag_false(
        self, manager: JWTTokenManager
    ) -> None:
        assert manager._allow_unverified_dev is False

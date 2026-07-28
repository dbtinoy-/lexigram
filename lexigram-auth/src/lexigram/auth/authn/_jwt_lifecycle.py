"""Token verification and lifecycle mixin for :class:`~lexigram.auth.authn.jwt.JWTTokenManager`.

This module is an internal implementation detail; import
:class:`~lexigram.auth.authn.jwt.JWTTokenManager` directly.
"""

from __future__ import annotations

from collections import OrderedDict
import hashlib
from typing import TYPE_CHECKING, Any, cast

import jwt

from lexigram.auth.authn._binding import TokenBindingConfig, verify_binding
from lexigram.auth.authn.blacklist import JWTBlacklist
from lexigram.auth.models import AuthToken
from lexigram.auth.models.user import User
from lexigram.contracts.auth.exceptions import TokenError as ContractsTokenError

if TYPE_CHECKING:
    from lexigram.auth.types import TokenPair
    from lexigram.contracts.audit import AuditLoggerProtocol
    from lexigram.contracts.auth.token import VerifiedToken
    from lexigram.contracts.core import HookRegistryProtocol
    from lexigram.logging import LoggerProtocol as Logger
    from lexigram.result import Result


class _JWTLifecycleMixin:
    """Mixin providing JWT token verification and lifecycle methods for :class:`JWTTokenManager`.

    All public attributes referenced here are initialised by
    ``JWTTokenManager.__init__``; they are declared below as class-level
    annotations solely to satisfy static type checkers.
    """

    # ── Attributes set by JWTTokenManager.__init__ ───────────────────────────
    algorithm: str
    access_expiration_hours: int
    refresh_expiration_days: int
    _required_audience: str | None
    _binding_config: TokenBindingConfig | None
    _blacklist_mgr: JWTBlacklist
    _verification_cache: OrderedDict[str, str]
    _verified_by_key: dict[str, str]
    logger: Logger
    _audit_logger: AuditLoggerProtocol | None
    _hooks: HookRegistryProtocol | None
    _allow_unverified_dev: bool

    @property
    def keys(self) -> dict[str, Any]:  # pragma: no cover
        """Live key material — provided by JWTTokenManager."""
        raise NotImplementedError

    @property
    def current_key_id(self) -> str:  # pragma: no cover
        """Active signing key ID — provided by JWTTokenManager."""
        raise NotImplementedError

    def _get_verification_key(self, kid: str) -> str:  # pragma: no cover
        """Return raw verification key — provided by JWTTokenManager."""
        raise NotImplementedError

    def create_token_pair(  # pragma: no cover
        self,
        user: User,
        additional_claims: dict[str, Any] | None = None,
        binding_context: dict[str, str] | None = None,
    ) -> AuthToken:
        """Create token pair — provided by _JWTCreationMixin."""
        raise NotImplementedError

    # ─────────────────────────────────────────────────────────────────────────

    async def _emit_action(self, hook_name: str, payload: object) -> None:
        """Emit a token lifecycle hook when a registry is available."""
        if self._hooks is None:
            return

        await self._hooks.call_action(hook_name, payload=payload)

    async def refresh_token(
        self, refresh_token: str
    ) -> Result[AuthToken, ContractsTokenError]:
        """Refresh an access token using a refresh token.

        Delegates to :meth:`refresh_access_token`.  Satisfies the updated
        ``TokenManagerProtocol`` protocol from ``lexigram.contracts.auth.token``.

        Args:
            refresh_token: The refresh token string.

        Returns:
            ``Ok(AuthToken)`` if the refresh token is valid, or
            ``Err(TokenError)`` for expected domain failures
            (expired, blacklisted, invalid).
        """
        from lexigram.auth.exceptions import (
            BlacklistedTokenError,
            TokenBlacklistedError,
        )
        from lexigram.auth.exceptions import TokenError as AuthTokenError
        from lexigram.result import Err, Ok

        try:
            return Ok(await self.refresh_access_token(refresh_token))
        except BlacklistedTokenError as e:
            return Err(TokenBlacklistedError(str(e)))  # type: ignore[arg-type]
        except AuthTokenError as e:
            return Err(ContractsTokenError(str(e)))

    async def refresh_with_rotation(
        self, refresh_token: str
    ) -> Result[TokenPair, ContractsTokenError]:
        """Rotate a refresh token and return a new access + refresh token pair.

        Implements one-time-use refresh token rotation (RTR).  The incoming
        refresh token is verified, immediately blacklisted, and a fresh token
        pair is issued.  If the token is already blacklisted (reuse-attack
        vector), all sessions for the affected user are revoked and the call
        returns ``Err``.

        Args:
            refresh_token: The current refresh token JWT string to exchange.

        Returns:
            ``Ok(TokenPair)`` with fresh ``access`` and ``refresh`` tokens on
            success, or ``Err(ContractsTokenError)`` for any expected domain
            failure (expired, invalid signature, already revoked).

        Raises:
            RuntimeError: On cache / infrastructure failures.
            OSError: On network-level failures.
            ConnectionError: On connection failures.
        """
        from lexigram.auth.exceptions import (
            BlacklistedTokenError,
            TokenBlacklistedError,
        )
        from lexigram.auth.exceptions import TokenError as AuthTokenError
        from lexigram.auth.types import TokenPair
        from lexigram.result import Err, Ok

        try:
            auth_token = await self.refresh_access_token(refresh_token)
            return Ok(
                TokenPair(
                    access=auth_token.token,
                    refresh=auth_token.refresh_token or "",
                )
            )
        except BlacklistedTokenError as e:
            return Err(TokenBlacklistedError(str(e)))  # type: ignore[arg-type]
        except AuthTokenError as e:
            return Err(ContractsTokenError(str(e)))

    async def verify_token(
        self,
        token: str,
        token_type: str = "access",  # noqa: S107  # not a password; identifies token kind
        expected_audience: str | None = None,
        required_scope: str | None = None,
        binding_context: dict[str, str] | None = None,
        *,
        allow_missing_audience: bool = False,
    ) -> Result[VerifiedToken, ContractsTokenError]:
        """Verify and decode a JWT token with support for multiple keys.

        Returns a ``Result`` rather than raising domain exceptions.  Only
        infrastructure failures (cache down, network errors) are still raised
        as exceptions so the event loop can propagate them properly.

        Args:
            token: The JWT token to verify.
            token_type: Expected token type ("access" or "refresh").
            expected_audience: Expected audience claim ("aud") for validation.
                Takes precedence over ``required_audience`` set on the manager.
            required_scope: Required scope claim for validation.
            binding_context: Optional request context dict for token binding.
            allow_missing_audience: When ``True``, audience validation is skipped
                entirely regardless of ``required_audience`` on the manager.
                Use only for trusted internal service paths that explicitly opt
                out of audience enforcement.

        Returns:
            ``Ok(VerifiedToken)`` if the token is valid and not revoked.
            ``Err(TokenError)`` for expected domain failures (expired,
            blacklisted, invalid signature, wrong type, audience mismatch, etc.).

        Raises:
            RuntimeError: If the cache backend is unavailable (infrastructure).
            OSError: On network-level failures (infrastructure).
            ConnectionError: On connection failures (infrastructure).
        """
        from lexigram.auth.exceptions import TokenAudienceError, TokenInvalidError
        from lexigram.auth.exceptions import (
            TokenBlacklistedError as ContractsBlacklistedError,
        )
        from lexigram.auth.exceptions import (
            TokenExpiredError as ContractsExpiredError,
        )
        from lexigram.contracts.auth.token import VerifiedToken
        from lexigram.result import Err, Ok

        try:
            # ── Unverified dev opt-in path ────────────────────────────────────
            # When allow_unverified_dev=True the token is decoded without any
            # signature check.  This path is ONLY reachable when explicitly
            # enabled (see TokenProvider / JWTConfig docs).
            if self._allow_unverified_dev:
                try:
                    payload = cast(
                        "dict[str, Any]",
                        jwt.decode(
                            token,
                            options={
                                "verify_signature": False,
                                "verify_exp": True,
                                "verify_aud": False,
                            },
                        ),
                    )
                except jwt.ExpiredSignatureError:
                    return Err(ContractsExpiredError("Token has expired"))  # type: ignore[arg-type]
                except (jwt.InvalidTokenError, ValueError) as e:
                    return Err(
                        TokenInvalidError(f"Invalid token (unverified path): {e}")  # type: ignore[arg-type]
                    )

                from datetime import UTC

                return Ok(
                    VerifiedToken(
                        user_id=payload.get("sub", ""),
                        email=payload.get("email", ""),
                        name=payload.get("name", ""),
                        roles=payload.get("roles", []),
                        permissions=payload.get("permissions", []),
                        expires_at=__import__("datetime").datetime.fromtimestamp(
                            payload.get("exp", 0), tz=UTC
                        ),
                        key_id="unverified",
                        token_type=token_type,
                        audience=None,
                    )
                )
            # ── End unverified dev path ───────────────────────────────────────

            # Compute a short token hash for the verification cache.
            # 16 hex chars (64 bits) is sufficient for an in-process lookup;
            # the full token is never stored.
            token_hash = hashlib.sha256(token.encode()).hexdigest()

            # Get key ID from header
            header = jwt.get_unverified_header(token)
            kid = header.get("kid", self.current_key_id)

            # Check if key exists
            if kid not in self.keys:
                return Err(TokenInvalidError("Unknown signing key ID"))  # type: ignore[arg-type]

            # Fast path: if we have already verified this exact token recently,
            # skip the kid-based lookup and go straight to the cached key_id.
            # Fall back to the per-kid cache, then the kid header itself.
            cached_key_id = self._verification_cache.get(token_hash)
            if cached_key_id and cached_key_id in self.keys:
                effective_key_id = cached_key_id
                self._verification_cache.move_to_end(
                    token_hash
                )  # mark as recently used
            else:
                # Try the key that last successfully verified this kid (fast path),
                # fall back to kid itself if the cached entry is absent or stale.
                effective_key_id = self._verified_by_key.get(kid, kid)
                if effective_key_id not in self.keys:
                    effective_key_id = kid

            # Verify with correct key
            verification_key = self._get_verification_key(effective_key_id)

            # Resolve the effective audience for this call:
            #   1. An explicit call-site audience always wins.
            #   2. Fall back to the manager-level required_audience.
            #   3. When allow_missing_audience=True, skip the check entirely.
            if allow_missing_audience:
                effective_audience: str | None = None
                decode_options: dict = {"verify_aud": False}
            else:
                effective_audience = expected_audience or self._required_audience
                decode_options = {"verify_aud": effective_audience is not None}
                if effective_audience is None:
                    import os

                    if os.getenv("LEX_ENV", "development") == "production":
                        self.logger.warning(
                            "jwt_verification_without_audience",
                            token_type=token_type,
                        )

            payload = cast(
                "dict[str, Any]",
                jwt.decode(
                    token,
                    verification_key,
                    algorithms=[self.algorithm],
                    audience=effective_audience,
                    options=decode_options,  # type: ignore[arg-type]
                ),
            )

            # Record which key_id successfully verified this kid and this token.
            self._verified_by_key[kid] = effective_key_id
            if len(self._verification_cache) >= 1000:
                self._verification_cache.popitem(last=False)  # evict LRU (oldest)
            self._verification_cache[token_hash] = effective_key_id

            # Check token type — only enforce if the payload explicitly declares one.
            # External JWTs (e.g. NextAuth HS256 tokens) omit the "type" claim; rejecting
            # them here would silently break all external-JWT auth flows.
            declared_type = payload.get("type")
            if declared_type is not None and declared_type != token_type:
                return Err(
                    TokenInvalidError(f"Invalid token type: expected {token_type}")  # type: ignore[arg-type]
                )

            # Validate audience explicitly if jwt.decode didn't handle it fully
            if effective_audience:
                token_aud = payload.get("aud")
                if isinstance(token_aud, list):
                    if effective_audience not in token_aud:
                        return Err(
                            TokenAudienceError(  # type: ignore[arg-type]
                                f"Invalid audience: {effective_audience}"
                            )
                        )
                elif token_aud != effective_audience:
                    return Err(
                        TokenAudienceError(f"Invalid audience: {effective_audience}")  # type: ignore[arg-type]
                    )

            # Validate scope if required
            if required_scope:
                token_scope = payload.get("scope", "")
                if required_scope not in token_scope.split():
                    return Err(
                        TokenInvalidError(f"Required scope missing: {required_scope}")  # type: ignore[arg-type]
                    )

            # Verify client binding if configured
            if self._binding_config and binding_context is not None:
                if not verify_binding(self._binding_config, payload, binding_context):
                    return Err(TokenInvalidError("Token binding mismatch"))  # type: ignore[arg-type]

            # Check if token is blacklisted — may raise RuntimeError (infra)
            if await self._is_token_blacklisted(token):
                return Err(ContractsBlacklistedError("Token has been revoked"))  # type: ignore[arg-type]

            from datetime import UTC

            return Ok(
                VerifiedToken(
                    user_id=payload.get("sub", ""),
                    email=payload.get("email", ""),
                    name=payload.get("name", ""),
                    roles=payload.get("roles", []),
                    permissions=payload.get("permissions", []),
                    expires_at=__import__("datetime").datetime.fromtimestamp(
                        payload.get("exp", 0), tz=UTC
                    ),
                    key_id=kid,
                    token_type=token_type,
                    audience=effective_audience,
                )
            )

        except jwt.ExpiredSignatureError:
            return Err(ContractsExpiredError("Token has expired"))  # type: ignore[arg-type]
        except jwt.InvalidAudienceError:
            return Err(TokenAudienceError("Invalid audience"))  # type: ignore[arg-type]
        except (jwt.InvalidTokenError, ValueError) as e:
            return Err(TokenInvalidError(f"Invalid token: {e}"))  # type: ignore[arg-type]

    async def logout(self, token: str) -> Result[None, ContractsTokenError]:
        """Invalidate a token by adding it to the blacklist.

        When a ``cache_service`` is configured the token hash is stored in
        the cache with key ``jwt:blacklist:{sha256_hex}`` and a TTL equal to
        the token's remaining lifetime.  When no cache is configured the hash
        is stored in an in-process set (cleared on process restart).

        Args:
            token: The JWT token to invalidate.

        Returns:
            ``Ok(None)`` on success or if the token was already expired.
            ``Err(TokenError)`` if the cache write failed.

        Raises:
            RuntimeError: On cache-level infrastructure failures.
            OSError: On network-level failures.
            ConnectionError: On connection failures.
        """
        from lexigram.auth.hooks import AuthTokenRevokedHook

        result = await self._blacklist_mgr.revoke(token)
        if result.is_ok():
            try:
                payload = cast(
                    "dict[str, Any]",
                    jwt.decode(
                        token,
                        options={
                            "verify_signature": False,
                            "verify_exp": False,
                            "verify_aud": False,
                        },
                    ),
                )
            except (jwt.DecodeError, jwt.InvalidTokenError, ValueError, TypeError):
                self.logger.warning("jwt_logout_hook_payload_decode_failed")
            else:
                await self._emit_action(
                    "auth.logout",
                    AuthTokenRevokedHook(
                        user_id=str(payload.get("sub", "")),
                        token_type=str(payload.get("type", "access")),
                    ),
                )
        return result

    async def logout_all_user_tokens(
        self, user_id: str
    ) -> Result[None, ContractsTokenError]:
        """Invalidate all tokens for a user by writing a user-level blacklist entry.

        Args:
            user_id: The user ID to invalidate all tokens for.

        Returns:
            ``Ok(None)`` on success. ``Err(TokenError)`` if the cache write failed.

        Raises:
            RuntimeError: If no cache backend is configured.
        """
        return await self._blacklist_mgr.revoke_all_for_user(user_id)

    async def _is_token_blacklisted(self, token: str) -> bool:
        """Check if a token is blacklisted.

        Args:
            token: The JWT token to check.

        Returns:
            ``True`` if the token should be rejected, ``False`` otherwise.
        """
        return await self._blacklist_mgr.is_blacklisted(token)

    async def refresh_access_token(self, refresh_token: str) -> AuthToken:
        """Create new access token from refresh token with rotation.

        Implements one-time-use refresh tokens (RTR). The used refresh token is
        blacklisted and a new refresh token is issued.

        If a blacklisted refresh token is presented, it indicates a potential
        reuse attack. In this case, all tokens for the user are invalidated
        immediately to prevent further compromise.

        Raises:
            TokenBlacklistedError: If token reuse is detected (domain failure).
            TokenError: For other domain failures (expired, invalid).
            RuntimeError: On infrastructure failures (cache, network).
        """
        from lexigram.auth.exceptions import (
            BlacklistedTokenError,
            TokenBlacklistedError,
        )
        from lexigram.auth.exceptions import TokenError as AuthTokenError

        result = await self.verify_token(refresh_token, "refresh")
        if result.is_err():
            error = result.unwrap_err()
            if isinstance(error, TokenBlacklistedError):
                # TOKEN REUSE DETECTED!
                # If we try to use a blacklisted refresh token, someone might have stolen it.
                # Invalidate EVERYTHING for this user.
                try:
                    unverified_payload = cast(
                        "dict[str, Any]",
                        jwt.decode(refresh_token, options={"verify_signature": False}),
                    )
                    user_id = unverified_payload.get("sub")
                    if user_id:
                        self.logger.warning(
                            "Refresh token reuse detected for user %s. Revoking all sessions.",
                            user_id,
                        )
                        await self.logout_all_user_tokens(user_id)
                except (RuntimeError, OSError, ConnectionError):
                    self.logger.exception(
                        "Failed to revoke user tokens after reuse detection",
                    )
                except (jwt.DecodeError, jwt.InvalidTokenError, ValueError, KeyError):
                    self.logger.exception(
                        "Unexpected error during session revocation",
                    )
                raise BlacklistedTokenError(
                    "Refresh token reuse detected. All sessions revoked.",
                ) from None
            # Other domain errors (expired, invalid)
            raise AuthTokenError(str(error)) from error

        verified = result.unwrap()

        # Blacklist the used refresh token (rotation)
        await self.logout(refresh_token)

        # Create new token pair from token claims
        user = User(
            user_id=verified.user_id,
            name=verified.name,
            email=verified.email,
            roles=verified.roles,
            permissions=verified.permissions,
        )

        from lexigram.auth.hooks import AuthTokenRefreshedHook

        token_pair = self.create_token_pair(user)
        await self._emit_action(
            "token.refreshed",
            AuthTokenRefreshedHook(user_id=verified.user_id, token_type="access"),
        )
        return token_pair

    async def get_user_from_token(
        self, token: str
    ) -> Result[VerifiedToken, ContractsTokenError]:
        """Extract user information from access token.

        Returns:
            ``Ok(VerifiedToken)`` if the token is a valid access token, or
            ``Err(TokenError)`` for expected domain failures.
        """
        return await self.verify_token(token, "access")

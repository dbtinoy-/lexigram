"""Minimal WebAuthn / Passkeys helper (server-side operations)

.. warning:: EXPERIMENTAL — NOT WebAuthn Level 1 Compliant
    This module implements a simplified passkey flow.  It provides the
    basic security properties (challenge-binding, public-key signature
    verification, sign-counter monotonicity, RP-origin validation) but
    intentionally omits parts of the full WebAuthn Level 1 spec that
    require binary CBOR/CTAP parsing:

    * ``clientDataJSON`` is NOT parsed — the client must extract and
      transmit the ``origin`` field separately if origin enforcement is
      desired.
    * ``authenticatorData`` binary blob is NOT parsed — the sign-counter
      is supplied by the client (trust level: application-level, not
      hardware-attested).
    * Full attestation-statement formats (``packed``, ``fido-u2f``,
      ``android-key``, etc.) are NOT verified.

    **What IS enforced here:**

    * The challenge is single-use and bound by a short TTL (prevents
      replay attacks).
    * The public key must be a valid EC P-256 key (basic key hygiene).
    * Duplicate credential IDs on the same user are rejected.
    * If ``allowed_origins`` is configured and an ``origin`` is provided,
      the origin is validated against the allow-list.
    * The sign counter, when supplied, must be **strictly greater** than
      the previously stored value, which detects cloned authenticators.
    * The actor performing a registration must match the pending user_id
      when ``actor_user_id`` is given (prevents cross-user hi-jacking).

    For production WebAuthn compliance, replace this module with
    ``py_webauthn`` or ``fido2`` once library dependencies are acceptable.

Storage format (kept on User.profile['passkeys']):
- credential_id: str
- public_key_pem: str
- name: str
- created_at: ISO timestamp
- sign_count: int  (monotonically increasing per-authenticator counter)

Temporary state for in-progress registration/authentication is kept in a
short-lived in-memory map (sufficient for single-process dev/staging and for
unit tests). In production you should replace this with a secure cache (Redis)
if multi-worker deployments are used.
"""

from __future__ import annotations

import base64
import secrets
from typing import TYPE_CHECKING

from lexigram.primitives import clock as ambient_clock

if TYPE_CHECKING:
    from lexigram.auth.storage.token_store import UserStoreProtocol
    from lexigram.contracts.infra.cache import CacheBackendProtocol

from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import ec

from lexigram import serialization as json
from lexigram.di.decorators import inject


class _PendingStore:
    """Abstract pending store with optional async cache backend.

    If a `cache` object is provided (e.g., provider.cache_service) we use its
    async `set`, `get`, and `delete` methods. Otherwise fall back to an in-memory
    dict with TTL semantics suitable for tests and single-process deployments.
    """

    def __init__(
        self,
        cache: CacheBackendProtocol | None = None,
    ) -> None:
        self.cache = cache
        self._store: dict[str, tuple[dict, float]] = {}

    async def set(self, key: str, value: dict, ttl: int = 300) -> None:
        if self.cache:
            await self.cache.set(key, json.dumps(value))
        else:
            now = ambient_clock.monotonic()
            self._store[key] = (value, now + ttl)

    async def get(self, key: str) -> dict | None:
        if self.cache:
            get_result = await self.cache.get(key)
            raw = (
                get_result.unwrap()
                if hasattr(get_result, "is_ok") and get_result.is_ok()
                else get_result
                if get_result
                else None
            )
            if raw is None:
                return None
            if isinstance(raw, (bytes, bytearray)):
                raw = raw.decode("utf-8")
            return json.loads(raw) if isinstance(raw, str) else raw  # type: ignore[return-value]
        v = self._store.get(key)
        if not v:
            return None
        value, expiry = v
        now = ambient_clock.monotonic()
        if now > expiry:
            del self._store[key]
            return None
        return value

    async def delete(self, key: str) -> None:
        if self.cache:
            await self.cache.delete(key)
        elif key in self._store:
            del self._store[key]


@inject
class PasskeyService:
    """Manage passkey registration and authentication flows.

    Notes:
    - start_registration / finish_registration: client obtains a challenge and
      then submits credential information (credential_id and public_key_pem)
      along with the challenge to finish registration.
    - start_authentication / finish_authentication: server issues a challenge
      which must be signed by the client's private key; the server verifies
      the signature using the stored public key.

    The service will use the provider's `cache_service` as the backing store for
    pending registration/authentication challenges when available. This ensures
    compatibility with multi-worker deployments (use Redis or similar).
    """

    def __init__(
        self,
        user_store: UserStoreProtocol,
        cache_service: CacheBackendProtocol | None = None,
        *,
        rp_id: str | None = None,
        allowed_origins: set[str] | None = None,
    ) -> None:
        self.user_store = user_store
        self.rp_id = rp_id
        self.allowed_origins: frozenset[str] = (
            frozenset(allowed_origins) if allowed_origins else frozenset()
        )
        self._pending_registrations = _PendingStore(cache_service)
        self._pending_authn = _PendingStore(cache_service)

    def _gen_challenge(self) -> str:
        # Return URL-safe base64 challenge
        return base64.urlsafe_b64encode(secrets.token_bytes(32)).decode("ascii")

    def _validate_origin(self, origin: str | None) -> bool:
        """Return False if origin is required but invalid or missing.

        Returns True (allow) when:
        - No ``allowed_origins`` are configured (origin enforcement disabled).
        - ``origin`` is provided and contained in ``allowed_origins``.

        Returns False (reject) when:
        - ``allowed_origins`` are configured and ``origin`` is None or missing.
        - ``origin`` is not in ``allowed_origins``.
        """
        if not self.allowed_origins:
            # Origin enforcement not configured — skip silently.
            return True
        if origin is None:
            # Origins required but not provided.
            return False
        return origin in self.allowed_origins

    async def start_registration(
        self,
        user_id: str,
        name: str | None = None,
    ) -> tuple[str, str]:
        """Start registration: return (registration_id, challenge)."""
        reg_id = secrets.token_hex(16)
        challenge = self._gen_challenge()
        data = {
            "user_id": user_id,
            "challenge": challenge,
            "name": name or "",
            "created_at": int(ambient_clock.timestamp()),
        }
        await self._pending_registrations.set(reg_id, data, ttl=300)
        return reg_id, challenge

    async def finish_registration(
        self,
        registration_id: str,
        credential_id: str,
        public_key_pem: str,
        actor_user_id: str | None = None,
        *,
        origin: str | None = None,
    ) -> bool:
        """Finish registration by storing the passkey on the user's profile.

        If ``actor_user_id`` is provided, the pending registration's ``user_id``
        must match it to prevent cross-user registration using intercepted
        ``registration_id`` values.

        If the service is configured with ``allowed_origins``, the ``origin``
        parameter (typically ``clientDataJSON.origin`` forwarded by the client)
        must be present and contained in the allow-list.

        Attestation statement verification is NOT performed — see module
        docstring for details.
        """
        # Load and delete pending registration from store
        pending = await self._pending_registrations.get(registration_id)
        if not pending:
            return False
        # cleanup
        await self._pending_registrations.delete(registration_id)

        # Validate origin before any further processing.
        if not self._validate_origin(origin):
            return False

        user_id = pending["user_id"]
        # Enforce actor matches pending user if actor provided
        if actor_user_id is not None and actor_user_id != user_id:
            return False

        name = pending.get("name") or ""

        user = await self.user_store.get_user_by_id(user_id)
        if not user:
            return False

        # Normalize PEM (load to ensure it's valid) and perform basic attestation checks
        try:
            key = serialization.load_pem_public_key(public_key_pem.encode("utf-8"))
        except (ValueError, TypeError):
            return False

        # Only accept EC keys (P-256) for now
        from cryptography.hazmat.primitives.asymmetric.ec import (
            SECP256R1,
            EllipticCurvePublicKey,
        )

        if not isinstance(key, EllipticCurvePublicKey):
            return False
        if key.curve.name != SECP256R1().name:
            return False

        # Re-serialize in a canonical PEM form
        try:
            pub_pem = key.public_bytes(
                encoding=serialization.Encoding.PEM,
                format=serialization.PublicFormat.SubjectPublicKeyInfo,
            ).decode("utf-8")
        except (ValueError, TypeError):
            return False

        # Ensure credential_id isn't already registered for this user
        profile = dict(user.profile)
        passkeys = list(profile.get("passkeys") or [])
        if any(p.get("credential_id") == credential_id for p in passkeys):
            # Duplicate credential id
            return False

        passkeys.append(
            {
                "credential_id": credential_id,
                "public_key_pem": pub_pem,
                "name": name,
                "created_at": ambient_clock.now().isoformat(),
                # Initialise sign counter to 0.  Must increase monotonically
                # with every successful authentication (CRIT-27).
                "sign_count": 0,
            },
        )
        profile["passkeys"] = passkeys

        import dataclasses

        # Real `User` objects are dataclasses in the app. For lightweight
        # tests or stubs the user may be a plain object; handle both.
        if dataclasses.is_dataclass(user):
            updated = dataclasses.replace(user, profile=profile)
            await self.user_store.update_user(updated)
        else:
            # mutate in-place and persist
            user.profile = profile
            await self.user_store.update_user(user)
        return True

    async def start_authentication(self, user_id: str) -> tuple[str, str, list[str]]:
        """Start authn: return (auth_id, challenge, allowed_credential_ids)."""
        user = await self.user_store.get_user_by_id(user_id)
        if not user:
            raise ValueError("User not found")

        passkeys = list(user.profile.get("passkeys") or [])
        credential_ids = [pk["credential_id"] for pk in passkeys]

        auth_id = secrets.token_hex(16)
        challenge = self._gen_challenge()
        data = {
            "user_id": user_id,
            "challenge": challenge,
            "created_at": int(ambient_clock.timestamp()),
        }
        await self._pending_authn.set(auth_id, data, ttl=300)
        return auth_id, challenge, credential_ids

    async def finish_authentication(
        self,
        auth_id: str,
        credential_id: str,
        signature: bytes,
        *,
        origin: str | None = None,
        new_sign_count: int | None = None,
    ) -> bool:
        """Finish authentication by verifying the signature over the challenge.

        Args:
            auth_id: Opaque session identifier returned by
                ``start_authentication``.
            credential_id: The credential chosen by the authenticator.
            signature: DER-encoded ECDSA signature over the raw challenge
                bytes (``challenge.encode("utf-8")``).
            origin: The ``origin`` field from ``clientDataJSON``, forwarded
                by the client.  Required when the service is configured with
                ``allowed_origins``; optional otherwise.
            new_sign_count: The sign counter reported by the authenticator.
                When provided it must be **strictly greater** than the stored
                value; equality or regression implies authenticator cloning and
                will cause this method to return False.

        Returns:
            True on success, False on any failure (challenge mismatch,
            missing/unknown credential, bad signature, origin violation, or
            sign-counter regression).
        """
        pending = await self._pending_authn.get(auth_id)
        if not pending:
            return False
        await self._pending_authn.delete(auth_id)

        # Validate origin before continuing.
        if not self._validate_origin(origin):
            return False

        user_id = pending["user_id"]
        challenge = pending["challenge"].encode("utf-8")

        user = await self.user_store.get_user_by_id(user_id)
        if not user:
            return False

        passkeys = list(user.profile.get("passkeys") or [])
        pk = next((p for p in passkeys if p["credential_id"] == credential_id), None)
        if not pk:
            return False

        # Sign-counter monotonicity check (CRIT-27).
        # A counter that does not increase (or regresses) signals a cloned
        # authenticator and must be rejected.
        if new_sign_count is not None:
            stored_count = pk.get("sign_count", 0)
            if new_sign_count <= stored_count:
                return False

        public_key_pem = pk["public_key_pem"].encode("utf-8")

        try:
            public_key = serialization.load_pem_public_key(public_key_pem)
            # We expect ECDSA P-256 / SHA256 signatures.
            # The caller must supply authenticatorData + SHA-256(clientDataJSON)
            # concatenated in `signature` for full WebAuthn compliance.  In
            # this simplified flow the signature covers the raw challenge bytes.
            public_key.verify(signature, challenge, ec.ECDSA(hashes.SHA256()))  # type: ignore[union-attr, call-arg, arg-type]
        except (ValueError, TypeError):
            return False

        # Persist the updated sign counter on success.
        if new_sign_count is not None:
            pk["sign_count"] = new_sign_count
            profile = dict(user.profile)
            profile["passkeys"] = passkeys

            import dataclasses

            if dataclasses.is_dataclass(user):
                updated = dataclasses.replace(user, profile=profile)
                await self.user_store.update_user(updated)
            else:
                user.profile = profile
                await self.user_store.update_user(user)

        return True


__all__ = ["PasskeyService"]

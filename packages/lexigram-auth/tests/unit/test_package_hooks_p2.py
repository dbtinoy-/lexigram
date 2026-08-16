"""P2 hook surface import verification for lexigram-auth."""

from __future__ import annotations

from dataclasses import FrozenInstanceError, is_dataclass

import pytest


def test_auth_hooks_root_module_exists() -> None:
    import lexigram.auth
    from lexigram.auth.hooks import (
        AuthAuthenticationFailedHook,
        AuthTokenIssuedHook,
        AuthTokenRefreshedHook,
        AuthTokenRevokedHook,
        AuthUserAuthenticatedHook,
    )

    assert AuthUserAuthenticatedHook.__name__ == "AuthUserAuthenticatedHook"
    assert AuthAuthenticationFailedHook.__name__ == "AuthAuthenticationFailedHook"
    assert AuthTokenIssuedHook.__name__ == "AuthTokenIssuedHook"
    assert AuthTokenRefreshedHook.__name__ == "AuthTokenRefreshedHook"
    assert AuthTokenRevokedHook.__name__ == "AuthTokenRevokedHook"
    assert lexigram.auth.AuthUserAuthenticatedHook is AuthUserAuthenticatedHook
    assert lexigram.auth.AuthAuthenticationFailedHook is AuthAuthenticationFailedHook
    assert lexigram.auth.AuthTokenIssuedHook is AuthTokenIssuedHook
    assert lexigram.auth.AuthTokenRefreshedHook is AuthTokenRefreshedHook
    assert lexigram.auth.AuthTokenRevokedHook is AuthTokenRevokedHook
    assert "AuthAuthenticationFailedHook" in lexigram.auth.__all__
    assert "AuthTokenIssuedHook" in lexigram.auth.__all__
    assert "AuthTokenRefreshedHook" in lexigram.auth.__all__
    assert "AuthTokenRevokedHook" in lexigram.auth.__all__
    assert "AuthUserAuthenticatedHook" in lexigram.auth.__all__


def test_auth_hook_payloads_are_frozen_and_keyword_only() -> None:
    from lexigram.auth.hooks import AuthUserAuthenticatedHook

    hook = AuthUserAuthenticatedHook(user_id="u1", method="password")

    assert is_dataclass(hook)

    with pytest.raises(TypeError):
        AuthUserAuthenticatedHook("u1", "password")  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        hook.user_id = "u2"  # type: ignore[misc]


def test_auth_token_refreshed_hook_is_frozen_and_keyword_only() -> None:
    from lexigram.auth.hooks import AuthTokenRefreshedHook

    hook = AuthTokenRefreshedHook(user_id="u1", token_type="access")

    assert is_dataclass(hook)

    with pytest.raises(TypeError):
        AuthTokenRefreshedHook("u1", "access")  # type: ignore[misc]

    with pytest.raises(FrozenInstanceError):
        hook.user_id = "u2"  # type: ignore[misc]

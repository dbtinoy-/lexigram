"""Typed helper for building session cookie keyword arguments from AdminAuthConfig."""

from __future__ import annotations

from typing import Literal, TypedDict

from lexigram.admin.config import AdminAuthConfig


class SessionCookieKwargs(TypedDict):
    """Keyword arguments for Starlette SessionMiddleware."""

    secret_key: str
    https_only: bool
    same_site: Literal["lax", "strict", "none"]
    max_age: int | None


def build_session_cookie_kwargs(cfg: AdminAuthConfig) -> SessionCookieKwargs:
    """Build SessionMiddleware kwargs from AdminAuthConfig.

    In production the cookie is Secure, HttpOnly (implied by SessionMiddleware),
    and SameSite=strict. In development, https_only is relaxed so local dev
    without HTTPS still works.
    """
    is_prod = cfg.env == "production"
    return SessionCookieKwargs(
        secret_key=cfg.session_secret,
        https_only=is_prod,
        same_site="strict" if is_prod else "lax",
        max_age=cfg.session_lifetime,
    )


__all__ = [
    "SessionCookieKwargs",
    "build_session_cookie_kwargs",
]

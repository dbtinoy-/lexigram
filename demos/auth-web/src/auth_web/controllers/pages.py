"""Server-rendered pages and account flows for the auth web demo."""

from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import RedirectResponse

from lexigram.auth.authn.services import AuthenticationService
from lexigram.auth.authn.user_service import UserService
from lexigram.auth.session.cookie_backend import SessionCookieBackend
from lexigram.logging import get_logger
from lexigram.ui import el, render_to_string
from lexigram.web import Controller, HTMLContent, get, post

from auth_web.services.session_repository import InMemorySessionRepository

logger = get_logger(__name__)


def _page(title: str, body: Any, error: str | None = None) -> HTMLContent:
    """Render one page; an optional error banner sits above the body."""
    if error:
        body = el("div", el("p", error, class_="error"), body)
    return HTMLContent(
        render_to_string(
            el(
                "html",
                el(
                    "head",
                    el("title", title),
                    el("link", rel="stylesheet", href="/static/style.css"),
                ),
                el("body", el("h1", title, class_="accent"), body),
            )
        )
    )


def _login_body(error: str | None = None) -> Any:
    banner = el("p", error, class_="error") if error else ""
    return el(
        "form",
        banner,
        el("input", name="email", type="email", placeholder="email", required=True),
        el(
            "input",
            name="password",
            type="password",
            placeholder="password",
            required=True,
        ),
        el("button", "Log in", type="submit"),
        method="post",
        action="/login",
    )


class AuthWebController(Controller):
    """Account lifecycle routes over lexigram-auth services."""

    def __init__(
        self,
        authentication: AuthenticationService,
        users: UserService,
        cookies: SessionCookieBackend,
        sessions: InMemorySessionRepository,
    ) -> None:
        self._authentication = authentication
        self._users = users
        self._cookies = cookies
        self._sessions = sessions

    @get("/")
    async def home(self, request: Request) -> RedirectResponse:
        user = await self._cookies.authenticate(request)
        target = "/profile" if user is not None else "/login"
        return RedirectResponse(url=target, status_code=307)

    @get("/login")
    async def login_form(self, request: Request) -> HTMLContent:
        return _page("Log in", _login_body())

    @post("/login")
    async def login_submit(self, request: Request) -> Any:
        form = await request.form()
        email = str(form.get("email", ""))
        password = str(form.get("password", ""))

        user = await self._authentication.authenticate_user(email, password)
        if user.is_err():
            logger.warning("login_failed", email=email)
            return _page("Log in", _login_body(), error=str(user.unwrap_err()))

        # SessionCookieBackend.login takes the RESPONSE object (it sets the
        # cookie on it) — build the redirect first, then hand it over.
        response = RedirectResponse(url="/profile", status_code=303)
        await self._cookies.login(response, user.unwrap().user_id)
        return response

    @post("/logout")
    async def logout(self, request: Request) -> RedirectResponse:
        response = RedirectResponse(url="/login", status_code=303)
        await self._cookies.logout(request, response)
        return response


__all__ = ["AuthWebController"]

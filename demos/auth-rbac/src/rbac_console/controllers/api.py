"""JSON API for the RBAC console — no HTML lives here."""

from __future__ import annotations

from typing import Any

from rbac_console.articles import ArticleStore
from rbac_console.personas import PERSONAS, PersonaDirectory
from starlette.requests import Request

from lexigram.auth.authn.user_service import UserService
from lexigram.auth.authz.service import AuthorizationService
from lexigram.auth.session.cookie_backend import SessionCookieBackend
from lexigram.logging import get_logger
from lexigram.serialization import loads as json_loads
from lexigram.web import Controller, JSONResponse, get, post

logger = get_logger(__name__)

PERSONA_PASSWORD = "Demo-Password-1"
# (action, resource) pairs the matrix renders; required permission is
# f"{resource}.{action}" per AuthorizationService's pattern grammar.
MATRIX_CHECKS: tuple[tuple[str, str], ...] = (
    ("view", "articles"),
    ("create", "articles"),
    ("update", "articles"),
    ("delete", "articles"),
    ("open", "admin_console"),
)


def _error(message: str, status: int) -> JSONResponse:
    return JSONResponse({"error": message}, status_code=status)


class RbacApiController(Controller):
    """RBAC API consumed by the UI's vanilla-JS client."""

    def __init__(
        self,
        users: UserService,
        authz: AuthorizationService,
        cookies: SessionCookieBackend,
        personas: PersonaDirectory,
        articles: ArticleStore,
    ) -> None:
        self._users = users
        self._authz = authz
        self._cookies = cookies
        self._personas = personas
        self._articles = articles

    @post("/api/login")
    async def login(self, request: Request) -> JSONResponse:
        """Log in as one of the seeded personas."""
        data = json_loads(await request.body())
        persona = str(data.get("persona", ""))
        if persona not in PERSONAS:
            return _error(f"unknown persona {persona!r}", 400)

        user = self._personas.get(persona)
        response = JSONResponse(
            {"ok": True, "persona": persona, "roles": list(user.roles)}
        )
        await self._cookies.login(response, user.user_id)
        return response

    @post("/api/logout")
    async def logout(self, request: Request) -> JSONResponse:
        response = JSONResponse({"ok": True})
        await self._cookies.logout(request, response)
        return response

    def _effective(self, user: Any) -> set[str]:
        """Explicit user permissions ∪ role-derived patterns (inherited)."""
        effective: set[str] = set()
        if getattr(user, "permissions", None):
            effective.update(user.permissions)
        for role in getattr(user, "roles", []) or []:
            effective |= self._authz.get_role_permissions(role)
        return effective

    @get("/api/me")
    async def me(self, request: Request) -> JSONResponse:
        user = await self._cookies.authenticate(request)
        if user is None:
            return _error("not authenticated", 401)
        return JSONResponse(
            {
                "email": user.email,
                "roles": list(user.roles),
                "permissions": sorted(self._effective(user)),
            }
        )

    @get("/api/matrix")
    async def matrix(self, request: Request) -> JSONResponse:
        """The permission grid computed live via authorize() per persona."""
        cells: dict[str, dict[str, bool]] = {}
        for role in PERSONAS:
            user = self._personas.get(role)
            row = {}
            for action, resource in MATRIX_CHECKS:
                verdict = await self._authz.authorize(user, action, resource)
                row[f"{resource}.{action}"] = (
                    verdict.unwrap() if verdict.is_ok() else False
                )
            cells[role] = row

        return JSONResponse(
            {
                "personas": self._personas.roles(),
                "checks": [
                    f"{resource}.{action}" for action, resource in MATRIX_CHECKS
                ],
                "cells": cells,
            }
        )

    @post("/api/try")
    async def try_check(self, request: Request) -> JSONResponse:
        """Run one authorize() verdict for a persona/action/resource triple."""
        data = json_loads(await request.body())
        role = str(data.get("role", ""))
        action = str(data.get("action", ""))
        resource = str(data.get("resource", ""))
        if role not in PERSONAS:
            return _error(f"unknown persona {role!r}", 400)

        user = self._personas.get(role)
        verdict = await self._authz.authorize(user, action, resource)
        granted = verdict.unwrap() if verdict.is_ok() else False
        return JSONResponse(
            {
                "granted": granted,
                "required": f"{resource}.{action}",
                "verdict": "Ok(True)" if granted else "Ok(False)",
            }
        )

    @get("/api/articles")
    async def list_articles(self, request: Request) -> JSONResponse:
        user = await self._cookies.authenticate(request)
        if user is None:
            return _error("not authenticated", 401)
        return JSONResponse(
            {
                "articles": [
                    {"id": a.id, "title": a.title, "body": a.body}
                    for a in self._articles.list()
                ]
            }
        )

    @post("/api/articles")
    async def create_article(self, request: Request) -> JSONResponse:
        user = await self._cookies.authenticate(request)
        if user is None:
            return _error("not authenticated", 401)
        allowed = await self._authz.authorize(user, "create", "articles")
        if not (allowed.unwrap() if allowed.is_ok() else False):
            return _error("forbidden: missing articles.create", 403)
        data = json_loads(await request.body())
        article = self._articles.create(
            title=str(data.get("title", "untitled")),
            body=str(data.get("body", "")),
        )
        return JSONResponse(
            {"ok": True, "article": {"id": article.id}}, status_code=201
        )


__all__ = ["RbacApiController"]

"""Regression tests for UsersResource (AdminUserEntity-backed resource).

UsersResource previously declared ``model = None`` ("set by DI or registry"),
so its create/edit forms rendered "No form configuration available".  It is
now bound to the canonical ``AdminUserEntity`` dataclass with
``form_exclude_fields`` covering secrets/framework-managed columns — the
generated form must expose safe fields only.
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request as StarletteRequest

from lexigram.admin.auth.entity import AdminUserEntity
from lexigram.admin.config import AdminConfig
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.forms.components import FormSchemaGenerator
from lexigram.admin.resources.base import Resource
from lexigram.admin.resources.form_renderer import FormRenderer
from lexigram.admin.resources.users import UserResource
from lexigram.admin.schema import BooleanField, MultiSelectField, TextField


def _create_request(path: str = "/admin/users/create") -> StarletteRequest:
    scope: dict = {
        "type": "http",
        "method": "GET",
        "path": path,
        "raw_path": path.encode(),
        "query_string": b"",
        "headers": [],
        "scheme": "http",
        "server": ("testserver", 80),
        "client": ("127.0.0.1", 1234),
        "asgi": {"version": "3.0", "spec_version": "2.0"},
        "path_params": {},
        "state": MagicMock(),
        "app": None,
        "session": {},
    }
    return StarletteRequest(scope)


def _form_names(html: str) -> set[str]:
    names = {
        n.replace("[]", "") for n in re.findall(r'<input[^>]*name="([^"]+)"', html)
    }
    names |= {
        n.replace("[]", "") for n in re.findall(r'<select[^>]*name="([^"]+)"', html)
    }
    names |= {
        n.replace("[]", "") for n in re.findall(r'<textarea[^>]*name="([^"]+)"', html)
    }
    return names


class TestUsersResource:
    def test_model_is_admin_user_entity(self) -> None:
        assert UserResource.model is AdminUserEntity

    def test_schema_generation_covers_safe_fields_only(self) -> None:
        schema = FormSchemaGenerator().from_pydantic(AdminUserEntity)
        by_name = {f.name: f for f in schema.fields}
        assert isinstance(by_name["username"], TextField)
        assert isinstance(by_name["email"], TextField)
        assert isinstance(by_name["roles"], MultiSelectField)
        assert isinstance(by_name["permissions"], MultiSelectField)
        assert isinstance(by_name["is_active"], BooleanField)
        assert isinstance(by_name["is_verified"], BooleanField)
        # Schema generation covers all entity fields; exclusion happens at
        # render time via form_exclude_fields (asserted in the render tests).
        assert isinstance(by_name["hashed_password"], TextField)

    @pytest.mark.asyncio
    async def test_create_form_renders_safe_inputs(self) -> None:
        renderer = FormRenderer(
            AdminConfig(prefix="/admin", title="Test"), "users", AdminRenderer()
        )
        response = await renderer.render_create(_create_request(), UserResource)
        html = response.body.decode("utf-8", "replace")
        names = _form_names(html)
        assert {
            "csrf_token",
            "username",
            "email",
            "roles",
            "permissions",
            "is_active",
            "is_verified",
        } <= names
        assert "hashed_password" not in names
        assert "No form configuration available" not in html

    @pytest.mark.asyncio
    async def test_form_exclude_fields_hook_is_honored(self) -> None:
        class FilteredResource(Resource):
            model = AdminUserEntity
            name = "filtered"
            form_exclude_fields = (
                "id",
                "created_at",
                "updated_at",
                "hashed_password",
                "email",
                "is_verified",
            )

        renderer = FormRenderer(
            AdminConfig(prefix="/admin", title="Test"), "filtered", AdminRenderer()
        )
        response = await renderer.render_create(
            _create_request(path="/admin/filtered/create"), FilteredResource
        )
        html = response.body.decode("utf-8", "replace")
        names = _form_names(html)
        assert {"csrf_token", "username", "roles", "permissions", "is_active"} <= names
        assert not {"email", "is_verified", "hashed_password"} & names

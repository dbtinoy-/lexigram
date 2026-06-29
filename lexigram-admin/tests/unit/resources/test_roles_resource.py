"""Regression tests for RolesResource (RBAC dataclass-backed resource).

RolesResource previously imported a nonexistent ``lexigram.admin.models.auth``
module, making the module unimportable.  It is now bound to the canonical
``RoleDefinition`` dataclass, and its create form must render schema fields with no
errors.
"""

from __future__ import annotations

import re
from unittest.mock import MagicMock

import pytest
from starlette.requests import Request as StarletteRequest

from lexigram.admin.config import AdminConfig
from lexigram.admin.engine.renderer import AdminRenderer
from lexigram.admin.forms.components import FormSchemaGenerator
from lexigram.contracts.auth import RoleDefinition
from lexigram.admin.resources.form_renderer import FormRenderer
from lexigram.admin.resources.roles import RolesResource
from lexigram.admin.schema import BooleanField, MultiSelectField, TextField


def _create_request() -> StarletteRequest:
    scope: dict = {
        "type": "http",
        "method": "GET",
        "path": "/admin/roles/create",
        "raw_path": b"/admin/roles/create",
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


class TestRolesResource:
    def test_model_is_rbac_admin_role(self) -> None:
        assert RolesResource.model is RoleDefinition

    def test_schema_generation_covers_role_fields(self) -> None:
        schema = FormSchemaGenerator().from_pydantic(RoleDefinition)
        by_name = {f.name: f for f in schema.fields}
        assert isinstance(by_name["name"], TextField)
        assert isinstance(by_name["description"], TextField)
        assert isinstance(by_name["permissions"], MultiSelectField)
        assert isinstance(by_name["inherits"], MultiSelectField)
        assert isinstance(by_name["is_system"], BooleanField)

    @pytest.mark.asyncio
    async def test_create_form_renders_schema_inputs(self) -> None:
        renderer = FormRenderer(
            AdminConfig(prefix="/admin", title="Test"), "roles", AdminRenderer()
        )
        response = await renderer.render_create(_create_request(), RolesResource)
        html = response.body.decode("utf-8", "replace")
        names = {
            n.replace("[]", "") for n in re.findall(r'<input[^>]*name="([^"]+)"', html)
        }
        names |= {
            n.replace("[]", "") for n in re.findall(r'<select[^>]*name="([^"]+)"', html)
        }
        names |= {
            n.replace("[]", "")
            for n in re.findall(r'<textarea[^>]*name="([^"]+)"', html)
        }
        assert {
            "csrf_token",
            "name",
            "description",
            "permissions",
            "inherits",
            "is_system",
        } <= names
        assert "No form configuration available" not in html

    def test_can_delete_blocks_system_role(self) -> None:
        """System roles cannot be deleted through the resource path."""
        resource = RolesResource()
        system = RoleDefinition(name="admin", is_system=True)
        assert resource.can_delete(system) is False

    def test_can_delete_blocks_super_admin_role(self) -> None:
        """The configured super-admin role is protected from deletion."""
        resource = RolesResource()
        assert (
            resource.can_delete(RoleDefinition(name="superadmin", is_system=False)) is False
        )

    def test_can_delete_allows_custom_roles(self) -> None:
        """Ordinary roles remain deletable."""
        resource = RolesResource()
        custom = RoleDefinition(name="editor", is_system=False)
        assert resource.can_delete(custom) is True

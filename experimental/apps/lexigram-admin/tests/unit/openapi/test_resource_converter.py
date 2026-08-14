from __future__ import annotations

from typing import Any

from lexigram.admin.openapi.resource_converter import (
    resource_to_schema,
    resources_to_openapi_spec,
)
from lexigram.admin.schema import (
    BooleanField,
    EmailField,
    IntegerField,
    SelectField,
    TextField,
)


class TestResourceToSchema:
    def test_basic_schema(self) -> None:
        fields = [
            TextField(name="name", required=True),
            EmailField(name="email", required=True),
            IntegerField(name="age", nullable=True),
        ]
        schema = resource_to_schema("users", fields)

        assert schema["type"] == "object"
        assert schema["title"] == "users"
        assert set(schema["properties"].keys()) == {"name", "email", "age"}
        assert set(schema["required"]) == {"name", "email"}

    def test_no_required_when_all_nullable(self) -> None:
        fields = [
            TextField(name="name", nullable=True),
            TextField(name="bio", nullable=True),
        ]
        schema = resource_to_schema("items", fields)
        assert "required" not in schema

    def test_property_types(self) -> None:
        fields = [
            TextField(name="name"),
            IntegerField(name="count"),
            BooleanField(name="active"),
        ]
        schema = resource_to_schema("test", fields)
        props = schema["properties"]
        assert props["name"]["type"] == "string"
        assert props["count"]["type"] == "integer"
        assert props["active"]["type"] == "boolean"


class StubResource:
    """Minimal resource stub for testing resources_to_openapi_spec."""

    def __init__(
        self,
        name: str,
        fields: list[Any],
        label: str | None = None,
    ) -> None:
        self.name = name
        self.fields = fields
        if label is not None:
            self.label = label


class TestResourcesToOpenAPISpec:
    def test_empty_resources(self) -> None:
        spec = resources_to_openapi_spec({})
        assert spec["openapi"] == "3.0.3"
        assert spec["info"]["title"] == "Admin API"
        assert spec["paths"] == {}
        assert spec["components"]["schemas"] == {}

    def test_single_resource(self) -> None:
        resource = StubResource(
            "users",
            fields=[
                TextField(name="name", nullable=False),
                EmailField(name="email"),
            ],
        )
        spec = resources_to_openapi_spec({"users": resource})

        assert "users.Resource" in spec["components"]["schemas"]
        assert "users.ListResponse" in spec["components"]["schemas"]

        assert "/api/users" in spec["paths"]
        assert "/api/users/{id}" in spec["paths"]

        list_path = spec["paths"]["/api/users"]
        assert "get" in list_path
        assert "post" in list_path

        detail_path = spec["paths"]["/api/users/{id}"]
        assert "get" in detail_path
        assert "put" in detail_path
        assert "delete" in detail_path

        tags = spec["tags"]
        assert len(tags) == 1
        assert tags[0]["name"] == "users"

    def test_multiple_resources(self) -> None:
        users = StubResource("users", fields=[TextField(name="name")])
        posts = StubResource("posts", fields=[TextField(name="title")])

        spec = resources_to_openapi_spec({"users": users, "posts": posts})

        assert len(spec["tags"]) == 2
        assert "/api/users" in spec["paths"]
        assert "/api/posts" in spec["paths"]

    def test_custom_title_and_version(self) -> None:
        resource = StubResource("items", fields=[TextField(name="name")])
        spec = resources_to_openapi_spec(
            {"items": resource},
            title="My Custom API",
            version="2.0.0",
        )
        assert spec["info"]["title"] == "My Custom API"
        assert spec["info"]["version"] == "2.0.0"

    def test_resource_without_fields(self) -> None:
        resource = StubResource("empty", fields=[])
        spec = resources_to_openapi_spec({"empty": resource})
        assert "empty.Resource" in spec["components"]["schemas"]
        schema = spec["components"]["schemas"]["empty.Resource"]
        assert schema["type"] == "object"
        assert schema["properties"] == {}

    def test_select_field_enum_in_schema(self) -> None:
        resource = StubResource(
            "users",
            fields=[
                SelectField(
                    name="role",
                    options=[("admin", "Admin"), ("user", "User")],
                ),
            ],
        )
        spec = resources_to_openapi_spec({"users": resource})
        schema = spec["components"]["schemas"]["users.Resource"]
        role_prop = schema["properties"]["role"]
        assert role_prop["enum"] == ["admin", "user"]

    def test_required_fields_in_required_list(self) -> None:
        resource = StubResource(
            "users",
            fields=[
                TextField(name="name", required=True),
                TextField(name="bio", required=False),
            ],
        )
        spec = resources_to_openapi_spec({"users": resource})
        schema = spec["components"]["schemas"]["users.Resource"]
        assert "name" in schema["required"]
        assert "bio" not in schema["required"]

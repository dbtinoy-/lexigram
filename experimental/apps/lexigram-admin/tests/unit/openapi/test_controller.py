from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

from lexigram.admin.openapi.controller import OpenAPIController
from lexigram.admin.schema import TextField
from lexigram.serialization import loads_str


class StubResource:
    def __init__(self, name: str, fields: list[Any]) -> None:
        self.name = name
        self.fields = fields


class TestOpenAPIController:
    async def test_get_spec_returns_json(self) -> None:
        resource = StubResource("users", fields=[TextField(name="name")])
        controller = OpenAPIController(resources={"users": resource})

        request = MagicMock()
        response = await controller.get_spec(request)

        assert response.status_code == 200
        assert response.media_type == "application/json"

    async def test_spec_content(self) -> None:
        resource = StubResource("users", fields=[TextField(name="name")])
        controller = OpenAPIController(resources={"users": resource})

        request = MagicMock()
        response = await controller.get_spec(request)

        spec = loads_str(response.body.decode())
        assert spec["openapi"] == "3.0.3"
        assert "users" in [t["name"] for t in spec["tags"]]
        assert "/api/users" in spec["paths"]

    async def test_empty_resources(self) -> None:
        controller = OpenAPIController(resources={})
        request = MagicMock()
        response = await controller.get_spec(request)

        spec = loads_str(response.body.decode())
        assert spec["paths"] == {}

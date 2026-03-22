"""Tests for the gateway served-model endpoints.

Covers the OpenAI/Anthropic/Gemini list shapes, the gemini forced
``/v1beta`` variants, the detail endpoints (including the 404 envelope
for unknown aliases and the 400 envelope for a missing alias), and the
wire-format sniffing rules.  Endpoints run through ``build_routes`` with
a catalog resolver double.
"""

from __future__ import annotations

from types import SimpleNamespace
from typing import Any

from lexigram.ai.relay.gateway.catalog import ModelCatalogService
from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.ai.relay.gateway.web.routes import MODEL_ROUTE_PATHS, build_routes
from lexigram.contracts.ai.relay import RelayChannel, RelayFormat
from lexigram.serialization import loads


class FakeModelCatalog:
    """Minimal ``ModelCatalogService`` double recording calls."""

    def __init__(self, service: ModelCatalogService) -> None:
        self._service = service
        self.calls: list[str] = []

    def list_openai(self) -> dict[str, Any]:
        """Record and delegate to the real list."""
        self.calls.append("list_openai")
        return self._service.list_openai()

    def list_claude(self) -> dict[str, Any]:
        """Record and delegate to the real list."""
        self.calls.append("list_claude")
        return self._service.list_claude()

    def list_gemini(self) -> dict[str, Any]:
        """Record and delegate to the real list."""
        self.calls.append("list_gemini")
        return self._service.list_gemini()

    def openai_detail(self, model: str) -> Any:
        """Record and delegate to the real detail lookup."""
        self.calls.append(f"openai_detail:{model}")
        return self._service.openai_detail(model)

    def gemini_detail(self, model: str) -> Any:
        """Record and delegate to the real detail lookup."""
        self.calls.append(f"gemini_detail:{model}")
        return self._service.gemini_detail(model)


class FakeCatalogResolver:
    """Async callable returning the configured catalog."""

    def __init__(self, catalog: FakeModelCatalog) -> None:
        self._catalog = catalog
        self.calls: list[Any] = []

    async def __call__(self, request: Any) -> FakeModelCatalog:
        """Record the request and return the fake catalog."""
        self.calls.append(request)
        return self._catalog


async def unused_gateway_resolver(request: Any) -> Any:
    """The gateway resolver must never be called for model routes."""
    raise AssertionError(f"gateway resolver called with {request!r}")


def routes() -> dict[str, Any]:
    """Raw model-list and detail endpoints from ``build_routes``."""
    catalog = FakeModelCatalog(real_catalog())
    tables = build_routes(
        unused_gateway_resolver,
        resolve_model_catalog=FakeCatalogResolver(catalog),
    )
    return {route.path: route for route in tables if route.path in MODEL_ROUTE_PATHS}


def real_catalog() -> ModelCatalogService:
    """A real catalog over a one-channel config."""
    return ModelCatalogService(
        RelayChannelRegistry(
            RelayGatewayConfig(
                channels=(
                    RelayChannel(
                        name="claude",
                        upstream_base_url="https://upstream.example.com/claude",
                        target_format=RelayFormat.CLAUDE,
                        models=("claude-sonnet",),
                    ),
                )
            )
        )
    )


def request(
    headers: dict[str, str] | None = None,
    path_params: dict[str, Any] | None = None,
) -> SimpleNamespace:
    """A minimal request double the endpoints can handle."""
    return SimpleNamespace(
        headers=headers or {},
        query_params={},
        path_params=path_params or {},
        state=SimpleNamespace(request_id="req-1", container=None),
    )


def status_and_body(response: Any) -> tuple[int, Any]:
    """Pull the status code and decoded body from a JSON response."""
    return response.status_code, loads(response.body)


def test_list_routes_are_get_only() -> None:
    for path in (
        "/v1/models",
        "/v1beta/models",
        "/v1/models/{model}",
        "/v1beta/models/{model}",
    ):
        assert path in routes()
        assert "GET" in routes()[path].methods


async def test_openai_list_default_shape() -> None:
    response = await routes()["/v1/models"].endpoint(request())
    status, payload = status_and_body(response)
    assert status == 200
    assert payload["object"] == "list"
    assert [entry["id"] for entry in payload["data"]] == ["claude-sonnet"]


async def test_anthropic_header_sniffs_claude_shape() -> None:
    response = await routes()["/v1/models"].endpoint(
        request(headers={"anthropic-version": "2023-06-01"})
    )
    _, payload = status_and_body(response)
    assert payload["data"][0]["type"] == "model"


async def test_google_header_sniffs_gemini_shape() -> None:
    response = await routes()["/v1/models"].endpoint(
        request(headers={"x-goog-api-key": "secret"})
    )
    _, payload = status_and_body(response)
    assert payload["models"][0]["name"] == "models/claude-sonnet"


async def test_google_query_param_sniffs_gemini_shape() -> None:
    req = request()
    req.query_params = {"key": "secret"}
    response = await routes()["/v1/models"].endpoint(req)
    _, payload = status_and_body(response)
    assert "models" in payload


async def test_v1beta_models_forces_gemini_shape() -> None:
    response = await routes()["/v1beta/models"].endpoint(request())
    _, payload = status_and_body(response)
    assert payload["models"][0]["name"] == "models/claude-sonnet"


async def test_openai_detail_shape() -> None:
    response = await routes()["/v1/models/{model}"].endpoint(
        request(path_params={"model": "claude-sonnet"})
    )
    status, payload = status_and_body(response)
    assert status == 200
    assert payload["id"] == "claude-sonnet"
    assert payload["object"] == "model"


async def test_gemini_detail_shape() -> None:
    response = await routes()["/v1beta/models/{model}"].endpoint(
        request(path_params={"model": "claude-sonnet"})
    )
    status, payload = status_and_body(response)
    assert status == 200
    assert payload["name"] == "models/claude-sonnet"


async def test_detail_404_for_unknown_model() -> None:
    response = await routes()["/v1/models/{model}"].endpoint(
        request(path_params={"model": "unknown"})
    )
    status, payload = status_and_body(response)
    assert status == 404
    assert payload["error"]["code"] == "MODEL_NOT_FOUND"


async def test_gemini_detail_404_envelope() -> None:
    response = await routes()["/v1beta/models/{model}"].endpoint(
        request(path_params={"model": "unknown"})
    )
    status, payload = status_and_body(response)
    assert status == 404
    assert payload["error"]["code"] == 404
    assert "status" in payload["error"]


async def test_detail_400_when_alias_missing() -> None:
    response = await routes()["/v1/models/{model}"].endpoint(request())
    status, payload = status_and_body(response)
    assert status == 400
    assert payload["error"]["code"] == "INVALID_REQUEST"

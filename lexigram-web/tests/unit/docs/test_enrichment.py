"""Tests for docs/enrichment.py — OpenAPIEnricher."""

from __future__ import annotations

import pytest

from lexigram.web.docs.enrichment import OpenAPIEnricher


class TestOpenAPIEnricherInit:
    def _empty_spec(self) -> dict:
        return {"paths": {}}

    def test_creates_components_section_if_missing(self) -> None:
        enricher = OpenAPIEnricher({})
        assert "components" in enricher.spec

    def test_creates_schemas_section_if_missing(self) -> None:
        enricher = OpenAPIEnricher({})
        assert "schemas" in enricher.spec["components"]

    def test_creates_security_schemes_section_if_missing(self) -> None:
        enricher = OpenAPIEnricher({})
        assert "securitySchemes" in enricher.spec["components"]

    def test_keeps_existing_components(self) -> None:
        spec = {"components": {"schemas": {"Existing": {"type": "object"}}}}
        enricher = OpenAPIEnricher(spec)
        assert "Existing" in enricher.spec["components"]["schemas"]


class TestAddSecurityScheme:
    def test_add_http_bearer_scheme(self) -> None:
        enricher = OpenAPIEnricher({})
        enricher.add_security_scheme("BearerAuth", "http")
        scheme = enricher.spec["components"]["securitySchemes"]["BearerAuth"]
        assert scheme["type"] == "http"
        assert scheme["scheme"] == "bearer"

    def test_add_http_bearer_with_format(self) -> None:
        enricher = OpenAPIEnricher({})
        enricher.add_security_scheme("BearerAuth", "http", bearer_format="JWT")
        scheme = enricher.spec["components"]["securitySchemes"]["BearerAuth"]
        assert scheme["bearerFormat"] == "JWT"

    def test_add_oauth2_scheme(self) -> None:
        enricher = OpenAPIEnricher({})
        flows = {"password": {"tokenUrl": "/token"}}
        enricher.add_security_scheme("OAuth2", "oauth2", flows=flows)
        scheme = enricher.spec["components"]["securitySchemes"]["OAuth2"]
        assert scheme["type"] == "oauth2"
        assert scheme["flows"] == flows

    def test_add_oauth2_scheme_empty_flows(self) -> None:
        enricher = OpenAPIEnricher({})
        enricher.add_security_scheme("OAuth2", "oauth2")
        assert enricher.spec["components"]["securitySchemes"]["OAuth2"]["flows"] == {}

    def test_add_api_key_scheme(self) -> None:
        enricher = OpenAPIEnricher({})
        enricher.add_security_scheme(
            "ApiKey",
            "apiKey",
            api_key_name="X-API-Key",
            api_key_in="header",
        )
        scheme = enricher.spec["components"]["securitySchemes"]["ApiKey"]
        assert scheme["type"] == "apiKey"
        assert scheme["name"] == "X-API-Key"
        assert scheme["in"] == "header"

    def test_add_api_key_defaults_to_name_and_header(self) -> None:
        enricher = OpenAPIEnricher({})
        enricher.add_security_scheme("MyKey", "apiKey")
        scheme = enricher.spec["components"]["securitySchemes"]["MyKey"]
        assert scheme["name"] == "MyKey"
        assert scheme["in"] == "header"

    def test_returns_self_for_chaining(self) -> None:
        enricher = OpenAPIEnricher({})
        result = enricher.add_security_scheme("BearerAuth", "http")
        assert result is enricher


class TestAddBearerAuth:
    def test_adds_bearer_auth_default_jwt(self) -> None:
        enricher = OpenAPIEnricher({})
        enricher.add_bearer_auth()
        scheme = enricher.spec["components"]["securitySchemes"]["BearerAuth"]
        assert scheme["bearerFormat"] == "JWT"

    def test_adds_bearer_auth_custom_format(self) -> None:
        enricher = OpenAPIEnricher({})
        enricher.add_bearer_auth(bearer_format="opaque")
        assert enricher.spec["components"]["securitySchemes"]["BearerAuth"]["bearerFormat"] == "opaque"

    def test_returns_self(self) -> None:
        enricher = OpenAPIEnricher({})
        assert enricher.add_bearer_auth() is enricher


class TestAddApiKeyAuth:
    def test_adds_api_key_with_defaults(self) -> None:
        enricher = OpenAPIEnricher({})
        enricher.add_api_key_auth()
        scheme = enricher.spec["components"]["securitySchemes"]["ApiKeyAuth"]
        assert scheme["type"] == "apiKey"
        assert scheme["name"] == "X-API-Key"

    def test_adds_api_key_with_custom_name_and_header(self) -> None:
        enricher = OpenAPIEnricher({})
        enricher.add_api_key_auth(name="MyAuth", header_name="X-Custom-Key")
        scheme = enricher.spec["components"]["securitySchemes"]["MyAuth"]
        assert scheme["name"] == "X-Custom-Key"

    def test_returns_self(self) -> None:
        enricher = OpenAPIEnricher({})
        assert enricher.add_api_key_auth() is enricher


class TestApplySecurityToAllPaths:
    def _spec_with_path(self) -> dict:
        return {
            "paths": {
                "/users": {
                    "get": {"summary": "List users", "responses": {}},
                    "post": {"summary": "Create user", "responses": {}},
                },
            },
        }

    def test_adds_security_to_all_operations(self) -> None:
        spec = self._spec_with_path()
        enricher = OpenAPIEnricher(spec)
        enricher.apply_security_to_all_paths(["BearerAuth"])
        assert "security" in spec["paths"]["/users"]["get"]
        assert "security" in spec["paths"]["/users"]["post"]

    def test_does_not_overwrite_existing_security(self) -> None:
        spec = self._spec_with_path()
        spec["paths"]["/users"]["get"]["security"] = [{"ExistingAuth": []}]
        enricher = OpenAPIEnricher(spec)
        enricher.apply_security_to_all_paths(["BearerAuth"])
        # Should keep existing security
        assert spec["paths"]["/users"]["get"]["security"] == [{"ExistingAuth": []}]

    def test_no_paths_is_safe(self) -> None:
        enricher = OpenAPIEnricher({})
        enricher.apply_security_to_all_paths(["BearerAuth"])  # No KeyError

    def test_returns_self(self) -> None:
        enricher = OpenAPIEnricher({})
        assert enricher.apply_security_to_all_paths([]) is enricher


class TestAddTag:
    def test_adds_new_tag(self) -> None:
        enricher = OpenAPIEnricher({})
        enricher.add_tag("Users")
        assert any(t["name"] == "Users" for t in enricher.spec["tags"])

    def test_adds_tag_with_description(self) -> None:
        enricher = OpenAPIEnricher({})
        enricher.add_tag("Users", description="User management")
        tag = enricher.spec["tags"][0]
        assert tag["description"] == "User management"

    def test_does_not_duplicate_existing_tag(self) -> None:
        enricher = OpenAPIEnricher({})
        enricher.add_tag("Users")
        enricher.add_tag("Users")
        assert len(enricher.spec["tags"]) == 1

    def test_updates_description_of_existing_tag(self) -> None:
        enricher = OpenAPIEnricher({})
        enricher.add_tag("Users")
        enricher.add_tag("Users", description="Updated desc")
        assert enricher.spec["tags"][0]["description"] == "Updated desc"

    def test_returns_self(self) -> None:
        enricher = OpenAPIEnricher({})
        assert enricher.add_tag("X") is enricher


class TestAddErrorSchema:
    def _spec_with_path(self) -> dict:
        return {
            "paths": {
                "/users": {
                    "get": {"responses": {}},
                },
            },
        }

    def test_adds_error_schema_to_components(self) -> None:
        enricher = OpenAPIEnricher(self._spec_with_path())
        enricher.add_error_schema("NotFound", 404)
        assert "ErrorNotFound" in enricher.spec["components"]["schemas"]

    def test_adds_error_response_to_operations(self) -> None:
        enricher = OpenAPIEnricher(self._spec_with_path())
        enricher.add_error_schema("NotFound", 404)
        assert "404" in enricher.spec["paths"]["/users"]["get"]["responses"]

    def test_does_not_overwrite_existing_response(self) -> None:
        spec = self._spec_with_path()
        spec["paths"]["/users"]["get"]["responses"]["404"] = {"description": "Custom 404"}
        enricher = OpenAPIEnricher(spec)
        enricher.add_error_schema("NotFound", 404)
        # Should keep existing response
        assert spec["paths"]["/users"]["get"]["responses"]["404"]["description"] == "Custom 404"

    def test_returns_self(self) -> None:
        enricher = OpenAPIEnricher({})
        assert enricher.add_error_schema("Error", 500) is enricher


class TestAddPaginationResponse:
    def test_adds_pagination_schema(self) -> None:
        enricher = OpenAPIEnricher({})
        item_schema = {"type": "object", "properties": {"id": {"type": "string"}}}
        enricher.add_pagination_response("UserList", item_schema)
        schema = enricher.spec["components"]["schemas"]["UserList"]
        assert schema["type"] == "object"
        assert "items" in schema["properties"]
        assert "meta" in schema["properties"]

    def test_returns_self(self) -> None:
        enricher = OpenAPIEnricher({})
        assert enricher.add_pagination_response("X", {}) is enricher


class TestAddFileUploadParameter:
    def test_returns_file_upload_parameter(self) -> None:
        enricher = OpenAPIEnricher({})
        param = enricher.add_file_upload_parameter("avatar")
        assert param["name"] == "avatar"
        assert param["type"] == "file"
        assert param["in"] == "formData"

    def test_required_defaults_false(self) -> None:
        enricher = OpenAPIEnricher({})
        param = enricher.add_file_upload_parameter("file")
        assert param["required"] is False

    def test_required_true(self) -> None:
        enricher = OpenAPIEnricher({})
        param = enricher.add_file_upload_parameter("file", required=True)
        assert param["required"] is True

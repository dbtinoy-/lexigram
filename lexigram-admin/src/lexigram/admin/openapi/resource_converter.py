from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.openapi.field_converter import field_to_openapi_property

if TYPE_CHECKING:
    from lexigram.admin.schema.base import SchemaField


def resource_to_schema(
    name: str,
    fields: list[SchemaField],
) -> dict[str, Any]:
    """Convert a resource's fields to an OpenAPI Schema Object.

    Args:
        name: Resource name (used as the schema title).
        fields: List of SchemaField instances.

    Returns:
        An OpenAPI Schema Object dict with ``type: object``, ``properties``,
        and ``required`` fields.
    """
    properties: dict[str, Any] = {}
    required: list[str] = []
    for field in fields:
        prop = field_to_openapi_property(field)
        properties[field.name] = prop
        if field.required:
            required.append(field.name)

    schema: dict[str, Any] = {
        "type": "object",
        "properties": properties,
        "title": name,
    }
    if required:
        schema["required"] = required
    return schema


def resources_to_openapi_spec(
    resources: dict[str, Any],
    *,
    title: str = "Admin API",
    version: str = "1.0.0",
) -> dict[str, Any]:
    """Convert admin resources to a full OpenAPI 3.0.3 specification.

    Args:
        resources: A ``{name: resource_instance}`` dict, where each resource
            has a ``fields`` attribute containing ``SchemaField`` instances.
        title: OpenAPI info title.
        version: OpenAPI spec version.

    Returns:
        A complete OpenAPI 3.0.3 spec dict with paths, schemas, and tags.
    """
    schemas: dict[str, Any] = {}
    paths: dict[str, Any] = {}
    tags: list[dict[str, str]] = []

    for resource_name, resource in resources.items():
        fields: list[SchemaField] = getattr(resource, "fields", []) or []
        label: str = getattr(resource, "label", resource_name)

        schema = resource_to_schema(resource_name, fields)
        schema_name = f"{resource_name}.Resource"
        schemas[schema_name] = schema

        list_schema_name = f"{resource_name}.ListResponse"
        schemas[list_schema_name] = {
            "type": "object",
            "properties": {
                "data": {
                    "type": "array",
                    "items": {"$ref": f"#/components/schemas/{schema_name}"},
                },
                "total": {"type": "integer"},
            },
        }

        tags.append({"name": resource_name, "description": label})

        prefix = f"/api/{resource_name}"

        paths[prefix] = {
            "get": {
                "tags": [resource_name],
                "summary": f"List {label}",
                "operationId": f"list{resource_name.title()}",
                "parameters": [
                    {
                        "name": "page",
                        "in": "query",
                        "schema": {"type": "integer", "default": 1},
                    },
                    {
                        "name": "per_page",
                        "in": "query",
                        "schema": {"type": "integer", "default": 15},
                    },
                ],
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": f"#/components/schemas/{list_schema_name}"
                                },
                            },
                        },
                    },
                },
            },
            "post": {
                "tags": [resource_name],
                "summary": f"Create {label}",
                "operationId": f"create{resource_name.title()}",
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{schema_name}"},
                        },
                    },
                },
                "responses": {
                    "201": {
                        "description": "Created",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": f"#/components/schemas/{schema_name}"
                                },
                            },
                        },
                    },
                },
            },
        }

        paths[f"{prefix}/{{id}}"] = {
            "get": {
                "tags": [resource_name],
                "summary": f"Get {label} by ID",
                "operationId": f"get{resource_name.title()}",
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                ],
                "responses": {
                    "200": {
                        "description": "Successful response",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": f"#/components/schemas/{schema_name}"
                                },
                            },
                        },
                    },
                },
            },
            "put": {
                "tags": [resource_name],
                "summary": f"Update {label}",
                "operationId": f"update{resource_name.title()}",
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                ],
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {
                            "schema": {"$ref": f"#/components/schemas/{schema_name}"},
                        },
                    },
                },
                "responses": {
                    "200": {
                        "description": "Updated",
                        "content": {
                            "application/json": {
                                "schema": {
                                    "$ref": f"#/components/schemas/{schema_name}"
                                },
                            },
                        },
                    },
                },
            },
            "delete": {
                "tags": [resource_name],
                "summary": f"Delete {label}",
                "operationId": f"delete{resource_name.title()}",
                "parameters": [
                    {
                        "name": "id",
                        "in": "path",
                        "required": True,
                        "schema": {"type": "string"},
                    },
                ],
                "responses": {
                    "204": {"description": "Deleted"},
                },
            },
        }

    spec: dict[str, Any] = {
        "openapi": "3.0.3",
        "info": {
            "title": title,
            "version": version,
        },
        "tags": tags,
        "paths": paths,
        "components": {
            "schemas": schemas,
        },
    }
    return spec


__all__ = ["resource_to_schema", "resources_to_openapi_spec"]

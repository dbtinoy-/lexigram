"""GraphQL introspection utilities.

This module provides utilities for GraphQL schema introspection,
including introspection query generation and result handling.
"""

from __future__ import annotations

from collections.abc import Iterator
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from strawberry import Schema as StrawberrySchema

    Schema = StrawberrySchema

from strawberry.extensions import SchemaExtension

from lexigram.graphql.exceptions import GraphQLError
from lexigram.logging import get_logger

logger = get_logger(__name__)


# Standard GraphQL introspection query
INTROSPECTION_QUERY = """
query IntrospectionQuery {
  __schema {
    queryType {
      name
    }
    mutationType {
      name
    }
    subscriptionType {
      name
    }
    types {
      ...FullType
    }
    directives {
      name
      description
      locations
      args {
        ...InputValue
      }
    }
  }
}

fragment FullType on __Type {
  kind
  name
  description
  fields(includeDeprecated: true) {
    name
    description
    args {
      ...InputValue
    }
    type {
      ...TypeRef
    }
    isDeprecated
    deprecationReason
  }
  inputFields {
    ...InputValue
  }
  interfaces {
    ...TypeRef
  }
  enumValues(includeDeprecated: true) {
    name
    description
    isDeprecated
    deprecationReason
  }
  possibleTypes {
    ...TypeRef
  }
}

fragment InputValue on __InputValue {
  name
  description
  type {
    ...TypeRef
  }
  defaultValue
}

fragment TypeRef on __Type {
  kind
  name
  ofType {
    kind
    name
    ofType {
      kind
      name
      ofType {
        kind
        name
        ofType {
          kind
          name
          ofType {
            kind
            name
            ofType {
              kind
              name
              ofType {
                kind
                name
              }
            }
          }
        }
      }
    }
  }
}
"""


# Simplified introspection query for basic schema info
SIMPLE_INTROSPECTION_QUERY = """
query SimpleIntrospectionQuery {
  __schema {
    queryType {
      name
      fields {
        name
        description
        type {
          name
          kind
        }
      }
    }
    mutationType {
      name
      fields {
        name
        description
        type {
          name
          kind
        }
      }
    }
    subscriptionType {
      name
      fields {
        name
        description
        type {
          name
          kind
        }
      }
    }
    types {
      name
      kind
      description
    }
  }
}
"""


def get_introspection_query(simplified: bool = False) -> str:
    """Get the GraphQL introspection query.

    Args:
        simplified: If True, return simplified query.

    Returns:
        Introspection query string.
    """
    if simplified:
        return SIMPLE_INTROSPECTION_QUERY
    return INTROSPECTION_QUERY


class IntrospectionHandler:
    """Handle GraphQL schema introspection.

    Provides utilities for introspecting GraphQL schemas,
    extracting type information, and generating schema documentation.

    Example:
        ```python
        handler = IntrospectionHandler(schema)

        # Get all types
        types = await handler.get_types()

        # Get fields for a type
        fields = await handler.get_type_fields("User")
        ```
    """

    def __init__(
        self,
        schema: Schema,
        enabled: bool = True,
    ) -> None:
        """Initialize the handler.

        Args:
            schema: Strawberry GraphQL schema.
            enabled: Whether introspection is enabled.
        """
        self._schema = schema
        self._enabled = enabled
        self._cache: dict[str, Any] = {}

    @property
    def enabled(self) -> bool:
        """Check if introspection is enabled."""
        return self._enabled

    def enable(self) -> None:
        """Enable introspection."""
        self._enabled = True

    def disable(self) -> None:
        """Disable introspection."""
        self._enabled = False

    async def introspect(
        self,
        simplified: bool = False,
    ) -> dict[str, Any]:
        """Run introspection query.

        Args:
            simplified: Use simplified query.

        Returns:
            Introspection result data.
        """
        if not self._enabled:
            raise ValueError("Introspection is disabled")

        cache_key = f"introspect_{simplified}"
        if cache_key in self._cache:
            return cast("dict[str, Any]", self._cache[cache_key])

        query = get_introspection_query(simplified)
        result = await self._schema.execute(query)

        if result.errors:
            raise ValueError(f"Introspection failed: {result.errors}")

        self._cache[cache_key] = result.data
        return cast("dict[str, Any]", result.data) or {}

    async def get_types(self) -> list[dict[str, Any]]:
        """Get all types in the schema.

        Returns:
            List of type definitions.
        """
        data = await self.introspect(simplified=True)
        schema = data.get("__schema", {})
        return cast("list[dict[str, Any]]", schema.get("types", []))

    async def get_type_fields(
        self,
        type_name: str,
    ) -> list[dict[str, Any]]:
        """Get fields for a type.

        Args:
            type_name: Name of the type.

        Returns:
            List of field definitions.
        """
        data = await self.introspect()
        schema = data.get("__schema", {})

        for type_def in schema.get("types", []):
            if type_def.get("name") == type_name:
                return type_def.get("fields") or []

        return []

    async def get_query_type(self) -> dict[str, Any] | None:
        """Get the query type.

        Returns:
            Query type definition or None.
        """
        data = await self.introspect(simplified=True)
        schema = data.get("__schema", {})
        return cast("dict[str, Any] | None", schema.get("queryType"))

    async def get_mutation_type(self) -> dict[str, Any] | None:
        """Get the mutation type.

        Returns:
            Mutation type definition or None.
        """
        data = await self.introspect(simplified=True)
        schema = data.get("__schema", {})
        return cast("dict[str, Any] | None", schema.get("mutationType"))

    async def get_subscription_type(self) -> dict[str, Any] | None:
        """Get the subscription type.

        Returns:
            Subscription type definition or None.
        """
        data = await self.introspect(simplified=True)
        schema = data.get("__schema", {})
        return cast("dict[str, Any] | None", schema.get("subscriptionType"))

    def clear_cache(self) -> None:
        """Clear the introspection cache."""
        self._cache.clear()

    async def generate_sdl(self) -> str:
        """Generate SDL (Schema Definition Language) from schema.

        Returns:
            Schema as SDL string.
        """
        from graphql import print_schema

        # Strawberry exposes the underlying graphql-core schema on ``_schema``
        # (or on ``schema`` with older versions); handle both cases.
        graphql_schema = getattr(self._schema, "_schema", None) or getattr(
            self._schema,
            "schema",
            self._schema,
        )
        return print_schema(graphql_schema)  # type: ignore[arg-type]


def _document_has_introspection(document: Any) -> bool:
    """Return True if any selection in the document targets an introspection field.

    Detection mirrors the depth validator's skip logic
    (:class:`~lexigram.graphql.security.depth.DepthLimitValidator`): fields
    whose names start with ``__``.
    """
    for definition in document.definitions:
        if not hasattr(definition, "selection_set") or definition.selection_set is None:
            continue
        to_visit = [definition.selection_set]
        while to_visit:
            selection_set = to_visit.pop()
            for selection in selection_set.selections:
                if hasattr(selection, "name") and selection.name is not None:
                    name = (
                        selection.name.value
                        if hasattr(selection.name, "value")
                        else str(selection.name)
                    )
                    if name.startswith("__"):
                        return True
                if hasattr(selection, "selection_set") and selection.selection_set:
                    to_visit.append(selection.selection_set)
    return False


class IntrospectionGuardExtension(SchemaExtension):
    """Reject every introspection operation.

    Registered by :class:`~lexigram.graphql.schema.builder.SchemaBuilderProtocol`
    only when introspection is *not* effectively enabled — that is, when
    ``IntrospectionConfig.enabled`` is False or the current environment is
    not listed in ``IntrospectionConfig.allowed_environments``. Production is
    additionally force-disabled at config validation time
    (``GraphQLConfig._auto_disable_introspection_in_production``), so the
    guard is guaranteed present on production deployments.
    """

    def on_validate(self) -> Iterator[None]:
        """Reject the operation when it targets introspection fields."""
        execution_context = self.execution_context
        document = execution_context.graphql_document
        if document is not None and _document_has_introspection(document):
            error = GraphQLError("Introspection is disabled")
            error.safe = (
                True  # amendment 2026-08-17: keep the message under default mask_errors
            )
            raise error
        yield


__all__ = [
    "IntrospectionGuardExtension",
    "IntrospectionHandler",
    "get_introspection_query",
]

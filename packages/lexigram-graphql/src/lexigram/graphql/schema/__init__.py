"""Schema module.

This module provides schema building utilities, decorators,
type definitions, and documentation generation for GraphQL schemas.
"""

from __future__ import annotations

from lexigram.graphql.schema.builder import (
    Schema,
    SchemaBuilderProtocol,
    create_schema,
)
from lexigram.graphql.schema.decorators import (
    field,
    mutation,
    query,
    resolver,
    subscription,
)
from lexigram.graphql.schema.documentation import (
    FieldDoc,
    SchemaDoc,
    SchemaDocumentationGenerator,
    TypeDoc,
    generate_schema_docs,
)
from lexigram.graphql.schema.types import (
    EnumType,
    InputType,
    InterfaceType,
    ObjectType,
    ScalarType,
    union_type,
)

__all__ = [
    "EnumType",
    "FieldDoc",
    "InputType",
    "InterfaceType",
    # Types
    "ObjectType",
    "ScalarType",
    # Builder
    "Schema",
    "SchemaBuilderProtocol",
    "SchemaDoc",
    # Documentation
    "SchemaDocumentationGenerator",
    "TypeDoc",
    "create_schema",
    "field",
    "generate_schema_docs",
    "mutation",
    # Decorators
    "query",
    "resolver",
    "subscription",
    "union_type",
]

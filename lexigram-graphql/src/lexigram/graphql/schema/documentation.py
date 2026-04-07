"""Automatic GraphQL documentation generation.

This module provides utilities for generating documentation
from GraphQL schemas.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass
class FieldDoc:
    """Documentation for a GraphQL field.

    Attributes:
        name: Field name.
        description: Field description.
        type: Field type.
        args: Field arguments.
    """

    name: str
    description: str | None = None
    type: str = ""
    args: list[dict[str, Any]] = field(default_factory=list)


@dataclass
class TypeDoc:
    """Documentation for a GraphQL type.

    Attributes:
        name: Type name.
        description: Type description.
        fields: Type fields.
    """

    name: str
    description: str | None = None
    fields: list[FieldDoc] = field(default_factory=list)


@dataclass
class SchemaDoc:
    """Complete schema documentation.

    Attributes:
        query_type: Query type name.
        mutation_type: Mutation type name.
        subscription_type: Subscription type name.
        types: All type documentations.
    """

    query_type: str | None = None
    mutation_type: str | None = None
    subscription_type: str | None = None
    types: list[TypeDoc] = field(default_factory=list)

    def to_markdown(self) -> str:
        """Generate Markdown documentation.

        Returns:
            Markdown-formatted documentation.
        """
        lines = ["# GraphQL Schema\n"]

        # Root types
        if self.query_type:
            lines.append(f"**Query Type**: `{self.query_type}`")
        if self.mutation_type:
            lines.append(f"**Mutation Type**: `{self.mutation_type}`")
        if self.subscription_type:
            lines.append(f"**Subscription Type**: `{self.subscription_type}`")

        lines.append("\n## Types\n")

        # Types
        for type_doc in self.types:
            lines.append(f"### {type_doc.name}\n")

            if type_doc.description:
                lines.append(f"{type_doc.description}\n")

            if type_doc.fields:
                lines.append("| Field | Type | Description |")
                lines.append("|-------|------|-------------|")

                for field_doc in type_doc.fields:
                    desc = field_doc.description or ""
                    lines.append(f"| {field_doc.name} | `{field_doc.type}` | {desc} |")

            lines.append("")

        return "\n".join(lines)


class SchemaDocumentationGenerator:
    """Generate documentation from GraphQL schemas.

    Example:
        from lexigram.logging import get_logger

        logger = get_logger(__name__)
        generator = SchemaDocumentationGenerator()
        doc = generator.generate(schema)

        # Output as Markdown
        markdown = doc.to_markdown()
        logger.info("schema_documentation", doc_length=len(markdown))
    """

    def generate(self, schema: Any) -> SchemaDoc:
        """Generate documentation from a schema.

        Args:
            schema: GraphQL schema.

        Returns:
            SchemaDoc with all documentation.
        """
        doc = SchemaDoc()

        # Get root types
        if hasattr(schema, "query"):
            doc.query_type = "Query"

        if hasattr(schema, "mutation"):
            doc.mutation_type = "Mutation"

        if hasattr(schema, "subscription"):
            doc.subscription_type = "Subscription"

        # Get types
        if hasattr(schema, "types"):
            for type_obj in schema.types:
                type_doc = self._document_type(type_obj)
                if type_doc:
                    doc.types.append(type_doc)

        return doc

    def _document_type(self, type_obj: Any) -> TypeDoc | None:
        """Document a single type.

        Args:
            type_obj: Type object.

        Returns:
            TypeDoc or None.
        """
        if not hasattr(type_obj, "name"):
            return None

        name = type_obj.name

        # Skip internal types
        if name.startswith("__"):
            return None

        type_doc = TypeDoc(
            name=name,
            description=getattr(type_obj, "description", None),
        )

        # Get fields
        if hasattr(type_obj, "fields"):
            for field_obj in type_obj.fields:
                field_doc = FieldDoc(
                    name=getattr(field_obj, "name", ""),
                    description=getattr(field_obj, "description", None),
                    type=str(getattr(field_obj, "type", "")),
                )
                type_doc.fields.append(field_doc)

        return type_doc


def generate_schema_docs(schema: Any) -> str:
    """Convenience function to generate schema documentation.

    Args:
        schema: GraphQL schema.

    Returns:
        Markdown-formatted documentation.
    """
    generator = SchemaDocumentationGenerator()
    doc = generator.generate(schema)
    return doc.to_markdown()


__all__ = [
    "FieldDoc",
    "SchemaDoc",
    "SchemaDocumentationGenerator",
    "TypeDoc",
    "generate_schema_docs",
]

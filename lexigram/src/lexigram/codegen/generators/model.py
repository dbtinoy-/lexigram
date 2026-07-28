"""Shared model generator."""

from __future__ import annotations

from lexigram.codegen.base import GeneratorBase
from lexigram.contracts.cli.generators import GenerationResult
from lexigram.contracts.cli.parsers import FieldSpec, parse_fields


class ModelGenerator(GeneratorBase):
    def generate(
        self,
        name: str,
        *,
        fields_str: str | None = None,
        table_name: str | None = None,
        table_doc: str | None = None,
        table_comment: str | None = None,
        dry_run: bool = False,
        force: bool = False,
        **options: object,
    ) -> GenerationResult:
        class_name = self._to_pascal_case(name)
        model_name = self._to_snake_case(name)
        file_path = self.output_dir / f"{model_name}.py"
        fields = parse_fields(fields_str or "")
        relationships = self._build_relationships(fields)
        content = self.render_template(
            "model.py.jinja2",
            {
                "class_name": class_name,
                "table_name": table_name or f"{model_name}s",
                "table_doc": table_doc,
                "table_args_block": self._build_table_args_block(table_comment),
                "imports_block": self._build_imports_block(fields, relationships),
                "field_block": self._build_field_block(fields, relationships),
            },
        )
        return self.write_file(file_path, content, dry_run=dry_run, force=force)

    def _build_table_args_block(self, table_comment: str | None) -> str:
        if table_comment is None:
            return ""
        return f'__table_args__ = {{"comment": {table_comment!r}}}'

    def _build_imports_block(
        self,
        fields: list[FieldSpec],
        relationships: list[dict[str, str]],
    ) -> str:
        field_names = {f.name for f in fields}
        sqlalchemy_types: list[str] = []
        needs_id = "id" not in field_names
        needs_timestamps = (
            "created_at" not in field_names and "updated_at" not in field_names
        )

        if needs_id or any(field.type in {"int", "integer"} for field in fields):
            sqlalchemy_types.append("Integer")
        if needs_timestamps or any(field.type == "datetime" for field in fields):
            sqlalchemy_types.append("DateTime")

        if any(field.type in {"str", "string"} for field in fields):
            sqlalchemy_types.append("String")
        if any(field.type == "text" for field in fields):
            sqlalchemy_types.append("Text")
        if any(field.type in {"bool", "boolean"} for field in fields):
            sqlalchemy_types.append("Boolean")
        if any(field.type == "float" for field in fields):
            sqlalchemy_types.append("Float")
        if any(field.fk is not None for field in fields):
            sqlalchemy_types.append("ForeignKey")

        orm_imports = ["Mapped", "mapped_column"]
        if relationships:
            orm_imports.append("relationship")

        sqlalchemy_imports = ", ".join(dict.fromkeys(sqlalchemy_types))
        orm_import_block = ", ".join(orm_imports)
        return "\n".join(
            [
                "from datetime import datetime",
                "",
                f"from sqlalchemy import {sqlalchemy_imports}",
                f"from sqlalchemy.orm import {orm_import_block}",
                "from sqlalchemy import func",
                "",
                "from lexigram.sql.base import Base",
            ]
        )

    def _build_field_block(
        self,
        fields: list[FieldSpec],
        relationships: list[dict[str, str]],
    ) -> str:
        field_names = {f.name for f in fields}
        lines: list[str] = []

        if "id" not in field_names:
            lines.append(
                "    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)"
            )

        for field in fields:
            lines.append(
                f"    {field.name}: {self._annotation_for(field)} = {self._mapped_column_for(field)}"
            )

        if "created_at" not in field_names and "updated_at" not in field_names:
            lines.extend(
                [
                    "",
                    "    created_at: Mapped[datetime] = mapped_column(",
                    "        DateTime(timezone=True),",
                    "        server_default=func.now(),",
                    "        nullable=False,",
                    "    )",
                    "    updated_at: Mapped[datetime] = mapped_column(",
                    "        DateTime(timezone=True),",
                    "        server_default=func.now(),",
                    "        onupdate=func.now(),",
                    "        nullable=False,",
                    "    )",
                ]
            )

        for relationship in relationships:
            relation_name = relationship["name"]
            model_name = relationship["model"]
            lines.extend(
                [
                    "",
                    f'    {relation_name}: Mapped["{model_name}Model"] = relationship("{model_name}Model")',
                ]
            )

        return "\n".join(lines)

    def _annotation_for(self, field: FieldSpec) -> str:
        base_type = self._python_type_for(field)
        if field.required:
            return f"Mapped[{base_type}]"
        return f"Mapped[{base_type} | None]"

    def _mapped_column_for(self, field: FieldSpec) -> str:
        args: list[str] = []
        kwargs: list[str] = []

        if field.fk is not None:
            args.extend(["Integer", f'ForeignKey("{field.fk}")'])
        else:
            args.append(self._column_type_for(field))

        if field.name == "id":
            kwargs.append("primary_key=True")
            if field.type in {"int", "integer"}:
                kwargs.append("autoincrement=True")

        if not field.required:
            kwargs.append("nullable=True")
        if field.unique:
            kwargs.extend(["unique=True", "index=True"])
        if field.default is not None:
            kwargs.append(f"default={self._default_expression(field)}")

        joined = ", ".join([*args, *kwargs])
        return f"mapped_column({joined})"

    def _column_type_for(self, field: FieldSpec) -> str:
        if field.type in {"str", "string"}:
            return "String(255)"
        if field.type == "text":
            return "Text"
        if field.type in {"int", "integer"}:
            return "Integer"
        if field.type == "float":
            return "Float"
        if field.type in {"bool", "boolean"}:
            return "Boolean"
        if field.type == "datetime":
            return "DateTime(timezone=True)"
        return "String(255)"

    def _python_type_for(self, field: FieldSpec) -> str:
        return {
            "bool": "bool",
            "boolean": "bool",
            "datetime": "datetime",
            "float": "float",
            "int": "int",
            "integer": "int",
            "str": "str",
            "string": "str",
            "text": "str",
        }.get(field.type, "str")

    def _default_expression(self, field: FieldSpec) -> str:
        default_value = field.default
        if default_value is None:
            return "None"
        if field.type in {"bool", "boolean"}:
            return "True" if default_value.lower() == "true" else "False"
        if field.type in {"float", "int", "integer"}:
            return default_value
        return repr(default_value)

    def _build_relationships(self, fields: list[FieldSpec]) -> list[dict[str, str]]:
        relationships: list[dict[str, str]] = []

        for field in fields:
            if field.fk is None:
                continue

            target = field.fk.split(".", 1)[0]
            relation_name = field.name
            if relation_name.endswith("_id"):
                relation_name = relation_name[:-3]
            elif relation_name.endswith("_ids"):
                relation_name = relation_name[:-4]

            relationships.append(
                {
                    "name": relation_name,
                    "model": self._to_pascal_case(self._singularize(target)),
                }
            )

        return relationships

    def _singularize(self, value: str) -> str:
        if value.endswith("ies"):
            return f"{value[:-3]}y"
        if value.endswith("s") and len(value) > 1:
            return value[:-1]
        return value

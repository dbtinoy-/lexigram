"""Admin Resource generator for lexigram-admin module."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen import FieldSpec, parse_fields
from lexigram.codegen.base import GenerationResult, GeneratorBase


class AdminResourceGenerator(GeneratorBase):
    """Generates an admin resource for the lexigram-admin module."""

    name = "admin"
    description = "Generate an admin resource for the admin panel"
    template_name = "admin_resource.py.jinja2"

    def __init__(self, output_dir: str = "src/admin/resources") -> None:
        super().__init__(
            output_dir=output_dir,
            template_root=Path(__file__).parent.parent / "templates",
        )

    def generate(
        self, name: str, **kwargs: Any
    ) -> GenerationResult:
        """Generate an admin resource file.

        Args:
            name: Model name (e.g., 'user' or 'User')
            **kwargs: Additional arguments including 'fields' and 'dry_run'

        Returns:
            GenerationResult with created/skipped files.
        """
        result = GenerationResult()
        dry_run: bool = kwargs.get("dry_run", False)
        force: bool = kwargs.get("force", False)

        fields_raw = kwargs.get("fields", "")
        fields = parse_fields(fields_raw) if fields_raw else []

        context = self._build_context(name, fields, kwargs)

        file_path = self.output_dir / f"{context['file_name']}.py"

        if file_path.exists() and not force:
            result.files_skipped.append(file_path)
            return result

        if dry_run:
            result.files_created.append(file_path)
            return result

        try:
            template = self.env.get_template(self.template_name)
            content = template.render(**context)
            self.output_dir.mkdir(parents=True, exist_ok=True)
            file_path.write_text(content)
            result.files_created.append(file_path)
        except (RuntimeError, OSError, AttributeError, LookupError):
            result.files_created.append(file_path)

        return result

    def _build_context(self, name: str, fields: list[FieldSpec], kwargs: dict) -> dict:
        """Build template context from fields."""
        model_name = name.capitalize()
        snake_name = self._to_snake(name)
        permission_prefix = snake_name.replace("_", "-")

        # Convert FieldSpec objects to dicts for template
        field_dicts = [
            {
                "name": field.name,
                "type": field.type,
                "required": field.required,
                "unique": field.unique,
                "fk": field.fk,
                "default": field.default,
            }
            for field in fields
        ]

        # Generate columns
        columns = self._generate_columns(field_dicts)

        # Generate filters
        filter_fields = self._generate_filters(field_dicts)

        # Generate form fields
        for field in field_dicts:
            field["pydantic_type"] = self._to_pydantic_type(field)
            field["form_field_kwargs"] = self._get_form_field_kwargs(field)

        return {
            "model_name": model_name,
            "resource_name": f"{model_name}Resource",
            "form_class_name": f"{model_name}Form",
            "model_class_name": f"{model_name}Model",
            "package_name": kwargs.get("package_name", "myapp"),
            "file_name": snake_name,
            "icon": kwargs.get("icon", self._get_default_icon(name)),
            "label": kwargs.get("label", model_name),
            "visible_in_sidebar": kwargs.get("visible", "True"),
            "columns": columns,
            "filter_fields": filter_fields,
            "fields": field_dicts,
            "permission_prefix": permission_prefix,
            "form_display_mode": kwargs.get("form_mode", "modal"),
            "page_size": kwargs.get("page_size", "20"),
            "default_sort": kwargs.get("sort", "created_at desc"),
        }

    def _to_snake(self, name: str) -> str:
        """Convert PascalCase to snake_case."""
        import re

        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    def _to_pydantic_type(self, field: dict) -> str:
        """Convert field type to Pydantic type."""
        field_type = field.get("type", "str").lower()
        nullable = field.get("nullable", False)

        type_map = {
            "str": "str",
            "string": "str",
            "text": "str",
            "int": "int",
            "integer": "int",
            "bigint": "int",
            "float": "float",
            "double": "float",
            "decimal": "float",
            "bool": "bool",
            "boolean": "bool",
            "date": "datetime",
            "datetime": "datetime",
            "uuid": "str",
            "json": "dict[str, Any]",
        }

        pydantic_type = type_map.get(field_type, "str")

        if nullable:
            return f"{pydantic_type} | None"
        return pydantic_type

    def _get_form_field_kwargs(self, field: dict) -> str:
        """Generate Pydantic Field kwargs for form."""
        kwargs = []

        # Label
        label = field.get("name", "").replace("_", " ").title()
        kwargs.append(f'label="{label}"')

        # Required (if not nullable)
        if not field.get("nullable", False):
            kwargs.append("min_length=1")

        # Default value
        default = field.get("default")
        if default is not None:
            if isinstance(default, str):
                kwargs.append(f"default='{default}'")
            else:
                kwargs.append(f"default={default}")
        elif field.get("nullable", False):
            kwargs.append("default=None")

        # Description
        description = field.get("description", "")
        if description:
            kwargs.append(f'description="{description}"')

        return ", ".join(kwargs) if kwargs else ""

    def _generate_columns(self, fields: list[dict]) -> list[str]:
        """Generate column definitions."""
        columns = []

        for field in fields:
            field_name = field.get("name", "")
            field_type = field.get("type", "str").lower()

            # Skip certain fields for columns
            if field_name in ("password", "hashed_password", "secret", "token"):
                continue

            if field_type in ("bool", "boolean"):
                columns.append(
                    f'BooleanColumn("{field_name}").label("{self._label(field_name)}")',
                )
            elif "date" in field_type or "time" in field_type:
                columns.append(
                    f'DateColumn("{field_name}").label("{self._label(field_name)}").format("%Y-%m-%d %H:%M")',
                )
            else:
                sortable = (
                    "sortable()"
                    if field_name in ("name", "email", "created_at", "updated_at")
                    else ""
                )
                columns.append(
                    f'TextColumn("{field_name}").label("{self._label(field_name)}"){sortable}',
                )

        return columns

    def _generate_filters(self, fields: list[dict]) -> list[str]:
        """Generate filter definitions."""
        filters = []

        for field in fields:
            field_name = field.get("name", "")
            field_type = field.get("type", "str").lower()

            # Skip certain fields
            if field_name in (
                "password",
                "hashed_password",
                "secret",
                "token",
                "content",
            ):
                continue

            if field_type in ("bool", "boolean"):
                filters.append(
                    f'BooleanFilter("{field_name}").label("{self._label(field_name)}")',
                )
            elif "date" in field_type or "time" in field_type:
                filters.append(
                    f'DateFilter("{field_name}").label("{self._label(field_name)}")',
                )
            else:
                filters.append(
                    f'TextFilter("{field_name}").label("{self._label(field_name)}")',
                )

        return filters

    def _label(self, name: str) -> str:
        """Convert field name to label."""
        return name.replace("_", " ").title()

    def _get_default_icon(self, name: str) -> str:
        """Get default icon based on model name."""
        name_lower = name.lower()

        icon_map = {
            "user": "users",
            "product": "package",
            "order": "shopping-cart",
            "category": "folder",
            "post": "file-text",
            "article": "book-open",
            "comment": "message-square",
            "image": "image",
            "file": "file",
            "tag": "tag",
            "role": "shield",
            "permission": "lock",
            "settings": "settings",
            "log": "activity",
            "report": "bar-chart",
            "analytics": "pie-chart",
        }

        return icon_map.get(name_lower, "box")


__all__ = ["AdminResourceGenerator"]

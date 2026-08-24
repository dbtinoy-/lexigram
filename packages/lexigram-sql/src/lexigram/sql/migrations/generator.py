"""Migration generation from Domain models for Lexigram Framework"""

from __future__ import annotations

from dataclasses import MISSING
from dataclasses import Field as DataclassField
from datetime import datetime
import inspect
from pathlib import Path
import re
from typing import Any, Union

from lexigram.domain import DomainModel
from lexigram.primitives import clock as ambient_clock
from lexigram.sql.migrations.base import MigrationError
from lexigram.sql.types import ColumnDefinition, SchemaDiff, TableDefinition


class ModelAnalyzer:
    """Analyzes Domain models to generate database schema definitions"""

    # Mapping of Python types to SQL types
    TYPE_MAPPING = {
        str: "VARCHAR",
        int: "INTEGER",
        float: "FLOAT",
        bool: "BOOLEAN",
        datetime: "TIMESTAMP",
        bytes: "BYTEA",
        # Add more mappings as needed
    }

    def analyze_model(
        self,
        model: type[DomainModel],
        table_name: str | None = None,
    ) -> TableDefinition:
        """Analyze a Domain model and return table definition"""
        if not issubclass(model, DomainModel):
            raise MigrationError(f"Model {model} must inherit from DomainModel")

        # Get table name from model or parameter
        table_name = table_name or self._get_table_name(model)

        # Analyze fields using dataclass fields API
        columns = []
        from dataclasses import fields as dataclass_fields

        for f in dataclass_fields(model):  # type: ignore[arg-type]
            # Convert field name to snake_case for database column
            column_name = self._camel_to_snake(f.name)
            column = self._analyze_field(column_name, f)
            columns.append(column)

        # Create table definition
        table_def = TableDefinition(name=table_name, columns=columns)

        # Add indexes and constraints based on field annotations
        self._add_indexes_and_constraints(table_def, model)

        return table_def

    def _get_table_name(self, model: type[DomainModel]) -> str:
        """Get table name from model"""
        # Check for table name in model metadata
        if hasattr(model, "Meta") and hasattr(model.Meta, "table_name"):
            return str(model.Meta.table_name)

        # Default to snake_case model name
        return self._camel_to_snake(model.__name__)

    def _camel_to_snake(self, name: str) -> str:
        """Convert CamelCase to snake_case"""

        s1 = re.sub("(.)([A-Z][a-z]+)", r"\1_\2", name)
        return re.sub("([a-z0-9])([A-Z])", r"\1_\2", s1).lower()

    def _analyze_field(
        self,
        field_name: str,
        field_info: DataclassField,
    ) -> ColumnDefinition:
        """Analyze a single field and return column definition"""
        # Get Python type
        python_type = field_info.type

        # Handle Optional types
        nullable = False
        if self._is_optional_type(python_type):
            nullable = True
            python_type = self._get_optional_inner_type(python_type)

        foreign_key: str | None = None
        # Handle List types (for foreign keys or arrays)
        if self._is_list_type(python_type):
            # This could be a foreign key relationship or array type
            inner_type = self._get_list_inner_type(python_type)
            if inspect.isclass(inner_type) and issubclass(inner_type, DomainModel):
                # Foreign key relationship
                foreign_table = self._get_table_name(inner_type)
                foreign_key = f"{foreign_table}.id"
                column_type = "INTEGER"  # Assuming ID is integer
            else:
                # Array type
                column_type = self._get_sql_type(inner_type) + "[]"
        else:
            column_type = self._get_sql_type(python_type)

        # Get field constraints from dataclass
        default_value = None
        if field_info.default is not MISSING:
            default_value = self._format_default_value(field_info.default)

        # Get extra metadata from field metadata (MappingProxyType from dataclasses)
        extra = field_info.metadata

        # Check for primary key
        primary_key = bool(extra.get("primary_key", False)) or field_name == "id"

        # Check for unique constraint
        unique = bool(extra.get("unique", False))

        # Check for index
        index = bool(extra.get("index", False))

        # Check for foreign key (metadata overrides auto-detected value)
        fk_raw = extra.get("foreign_key")
        if fk_raw is not None:
            foreign_key = str(fk_raw)

        # Get comment
        description = extra.get("description", "")

        return ColumnDefinition(
            name=field_name,
            type_sql=column_type,
            nullable=nullable,
            default=default_value,
            primary_key=primary_key,
            unique=unique,
            index=index,
            foreign_key=foreign_key,
            comment=description,
        )

    def _is_optional_type(self, type_hint: Any) -> bool:
        """Check if type is Optional (supports PEP 604 unions and typing.Union)."""
        # Handle typing.Union (has __origin__ and __args__)
        if hasattr(type_hint, "__origin__") and type_hint.__origin__ is Union:
            return type(None) in getattr(type_hint, "__args__", ())

        # Handle PEP 604 (X | Y) which may expose __args__ without __origin__
        args = getattr(type_hint, "__args__", None)
        if args is not None:
            return type(None) in args

        return False

    def _get_optional_inner_type(self, type_hint: Any) -> Any:
        """Get the inner type from Optional[T]"""
        return next(arg for arg in type_hint.__args__ if arg is not type(None))

    def _is_list_type(self, type_hint: Any) -> bool:
        """Check if type is List"""
        if hasattr(type_hint, "__origin__"):
            return type_hint.__origin__ is list
        return False

    def _get_list_inner_type(self, type_hint: Any) -> Any:
        """Get the inner type from List[T]"""
        return type_hint.__args__[0]

    def _get_sql_type(self, python_type: Any) -> str:
        """Convert Python type to SQL type"""
        # Handle direct type mappings
        if python_type in self.TYPE_MAPPING:
            return self.TYPE_MAPPING[python_type]

        # Handle string annotations
        if isinstance(python_type, str):
            # This is a forward reference, return VARCHAR as default
            return "VARCHAR"

        # Handle classes that might be enums or custom types
        if inspect.isclass(python_type):
            if issubclass(python_type, str):
                return "VARCHAR"
            if issubclass(python_type, int):
                return "INTEGER"
            if hasattr(python_type, "__members__"):  # Enum
                return "VARCHAR"  # Store enum as string

        # Default to VARCHAR for unknown types
        return "VARCHAR"

    def _format_default_value(self, value: Any) -> str:
        """Format default value for SQL"""
        if isinstance(value, str):
            return f"'{value}'"
        if isinstance(value, bool):
            return str(value).upper()
        if isinstance(value, (int, float)):
            return str(value)
        if value is None:
            return "NULL"
        return str(value)

    def _add_indexes_and_constraints(
        self,
        table_def: TableDefinition,
        model: type[DomainModel],
    ) -> None:
        """Add indexes and constraints based on model metadata"""
        # Check for model-level metadata
        if hasattr(model, "Meta"):
            meta = model.Meta

            # Add table indexes
            if hasattr(meta, "indexes"):
                table_def.indexes.extend(meta.indexes)

            # Add table constraints
            if hasattr(meta, "constraints"):
                table_def.constraints.extend(meta.constraints)


class MigrationGenerator:
    """Generates Alembic migration files from schema differences"""

    def __init__(self, migrations_path: str | Path) -> None:
        self.migrations_path = Path(migrations_path)
        self.analyzer = ModelAnalyzer()

    def generate_migration_from_models(
        self,
        models: list[type[DomainModel]],
        message: str = "Auto-generated migration",
        revision: str | None = None,
    ) -> str:
        """Generate migration from Domain models"""
        # Analyze all models
        table_definitions = [self.analyzer.analyze_model(m) for m in models]

        # For now, assume all tables need to be created
        # In a full implementation, this would compare with existing schema
        schema_diff = SchemaDiff(
            tables_to_create=table_definitions,
            tables_to_drop=[],
            columns_to_add={},
            columns_to_drop={},
            columns_to_modify={},
            indexes_to_add={},
            indexes_to_drop={},
            constraints_to_add={},
            constraints_to_drop={},
        )

        # Generate migration content
        migration_content = self._generate_migration_content(
            schema_diff,
            message,
            revision,
        )

        # Write migration file
        migration_file = self._create_migration_file(migration_content, message)

        return str(migration_file)

    def _generate_migration_content(
        self,
        schema_diff: SchemaDiff,
        message: str,
        revision: str | None,
    ) -> str:
        """Generate the content of the migration file"""
        # Generate upgrade operations
        upgrade_ops: list[str] = []

        # Create tables
        upgrade_ops.extend(
            self._generate_create_table_sql(table)
            for table in schema_diff.tables_to_create
        )

        # Add columns
        upgrade_ops.extend(
            self._generate_add_column_sql(table_name, column)
            for table_name, columns in schema_diff.columns_to_add.items()
            for column in columns
        )

        # Create indexes
        upgrade_ops.extend(
            self._generate_create_index_sql(table_name, index)
            for table_name, indexes in schema_diff.indexes_to_add.items()
            for index in indexes
        )

        # Generate downgrade operations (reverse of upgrade)
        downgrade_ops: list[str] = []

        # Drop indexes
        downgrade_ops.extend(
            self._generate_drop_index_sql(table_name, index)
            for table_name, indexes in schema_diff.indexes_to_add.items()
            for index in indexes
        )

        # Drop columns
        downgrade_ops.extend(
            self._generate_drop_column_sql(table_name, column)
            for table_name, columns in schema_diff.columns_to_add.items()
            for column in columns
        )

        # Drop tables
        downgrade_ops.extend(
            self._generate_drop_table_sql(table.name)
            for table in reversed(schema_diff.tables_to_create)
        )

        # Format the migration content
        return self._format_migration_template(
            message,
            revision,
            upgrade_ops,
            downgrade_ops,
        )

    def _generate_create_table_sql(self, table: TableDefinition) -> str:
        """Generate CREATE TABLE SQL"""
        columns_sql = []
        for column in table.columns:
            col_sql = f"    sa.Column('{column.name}', {column.type_sql}"

            if not column.nullable:
                col_sql += ", nullable=False"

            if column.default:
                col_sql += f", default={column.default}"

            if column.primary_key:
                col_sql += ", primary_key=True"

            if column.unique:
                col_sql += ", unique=True"

            if column.foreign_key:
                col_sql += f", sa.ForeignKey('{column.foreign_key}')"

            col_sql += ")"

            if column.comment:
                col_sql += f".comment('{column.comment}')"

            columns_sql.append(col_sql)

        columns_str = ",\n".join(columns_sql)

        # Add table-level constraints and indexes
        table_args = []

        # Add indexes
        for index in table.indexes:
            index_sql = self._generate_index_definition(table.name, index)
            table_args.append(index_sql)

        table_args_str = ""
        if table_args:
            table_args_str = ",\n" + ",\n".join(table_args)

        return f"""op.create_table('{table.name}',
{columns_str}{table_args_str}
)"""

    def _generate_add_column_sql(
        self,
        table_name: str,
        column: ColumnDefinition,
    ) -> str:
        """Generate ADD COLUMN SQL"""
        col_sql = f"sa.Column('{column.name}', {column.type_sql}"

        if not column.nullable:
            col_sql += ", nullable=False"

        if column.default:
            col_sql += f", default={column.default}"

        if column.primary_key:
            col_sql += ", primary_key=True"

        if column.unique:
            col_sql += ", unique=True"

        if column.foreign_key:
            col_sql += f", sa.ForeignKey('{column.foreign_key}')"

        col_sql += ")"

        return f"op.add_column('{table_name}', {col_sql})"

    def _generate_drop_column_sql(
        self,
        table_name: str,
        column: ColumnDefinition,
    ) -> str:
        """Generate DROP COLUMN SQL"""
        return f"op.drop_column('{table_name}', '{column.name}')"

    def _generate_create_index_sql(
        self,
        table_name: str,
        index_def: dict[str, Any],
    ) -> str:
        """Generate CREATE INDEX SQL"""
        index_name = index_def.get(
            "name",
            f"ix_{table_name}_{'_'.join(index_def['columns'])}",
        )
        columns = index_def["columns"]
        unique = index_def.get("unique", False)

        if unique:
            return f"op.create_index('{index_name}', '{table_name}', {columns}, unique=True)"
        return f"op.create_index('{index_name}', '{table_name}', {columns})"

    def _generate_drop_index_sql(
        self,
        table_name: str,
        index_def: dict[str, Any],
    ) -> str:
        """Generate DROP INDEX SQL"""
        index_name = index_def.get(
            "name",
            f"ix_{table_name}_{'_'.join(index_def['columns'])}",
        )
        return f"op.drop_index('{index_name}')"

    def _generate_drop_table_sql(self, table_name: str) -> str:
        """Generate DROP TABLE SQL"""
        return f"op.drop_table('{table_name}')"

    def _generate_index_definition(
        self,
        table_name: str,
        index_def: dict[str, Any],
    ) -> str:
        """Generate index definition for table args"""
        index_name = index_def.get(
            "name",
            f"ix_{table_name}_{'_'.join(index_def['columns'])}",
        )
        columns = index_def["columns"]
        unique = index_def.get("unique", False)

        columns_str = ", ".join(f"'{col}'" for col in columns)

        if unique:
            return f"sa.Index('{index_name}', {columns_str}, unique=True)"
        return f"sa.Index('{index_name}', {columns_str})"

    def _format_migration_template(
        self,
        message: str,
        revision: str | None,
        upgrade_ops: list[str],
        downgrade_ops: list[str],
    ) -> str:
        """Format the migration file template"""
        upgrade_str = "\n    ".join(upgrade_ops) if upgrade_ops else "pass"
        downgrade_str = "\n    ".join(downgrade_ops) if downgrade_ops else "pass"

        rev_id = revision or "auto_generated"

        return f'''"""{message}

Revision ID: {{up_revision}}
Revises: {{down_revision}}
Create Date: {{create_date}}

"""
from typing import Sequence

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "{rev_id}"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade database schema."""
    {upgrade_str}


def downgrade() -> None:
    """Downgrade database schema."""
    {downgrade_str}
'''

    def _create_migration_file(self, content: str, message: str) -> Path:
        """Create the migration file"""
        # Create versions directory if it doesn't exist
        versions_dir = self.migrations_path / "versions"
        versions_dir.mkdir(parents=True, exist_ok=True)

        # Generate filename
        now = ambient_clock.now()
        timestamp = now.strftime("%Y%m%d_%H%M%S") if now else "000000_000000"
        safe_message = "_".join(message.lower().split())
        filename = f"{timestamp}_{safe_message}.py"

        # Write file
        migration_file = versions_dir / filename
        migration_file.write_text(content)

        return migration_file

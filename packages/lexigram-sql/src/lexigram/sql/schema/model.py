"""Declarative schema model system for lexigram-sql.

Provides a Prisma/Django-inspired model definition system:

    from lexigram.sql.schema import Model, Field, Index, Relationship

    class User(Model):
        __tablename__ = "users"
        __indexes__ = [Index("idx_users_email", "email", unique=True)]

        id = Field(UUID, primary_key=True)
        email = Field(str, max_length=255, unique=True, nullable=False)
        name = Field(str, max_length=100)
        is_active = Field(bool, default=True)
        department_id = Field(UUID, foreign_key="departments.id")

        class Meta:
            soft_delete = True
            timestamps = True
            ordering = ["-created_at"]
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
import re
from typing import Any
from uuid import UUID

from lexigram.logging import get_logger

logger = get_logger(__name__)

_SENTINEL = object()


# ------------------------------------------------------------------
# Field Descriptor
# ------------------------------------------------------------------


class FieldType(StrEnum):
    """Supported database field types for cross-dialect mapping."""

    STRING = "string"
    TEXT = "text"
    INTEGER = "integer"
    BIGINT = "bigint"
    FLOAT = "float"
    DECIMAL = "decimal"
    BOOLEAN = "boolean"
    DATE = "date"
    DATETIME = "datetime"
    TIMESTAMP = "timestamp"
    UUID = "uuid"
    JSON = "json"
    JSONB = "jsonb"
    BINARY = "binary"
    ARRAY = "array"


# Python type → FieldType mapping
_TYPE_MAP: dict[type, FieldType] = {
    str: FieldType.STRING,
    int: FieldType.INTEGER,
    float: FieldType.FLOAT,
    bool: FieldType.BOOLEAN,
    datetime: FieldType.DATETIME,
    UUID: FieldType.UUID,
    bytes: FieldType.BINARY,
    dict: FieldType.JSON,
    list: FieldType.ARRAY,
}


class Field:
    """Database column descriptor with validation and type mapping.

    Attributes:
        python_type: The Python type for this field.
        primary_key: Whether this is the primary key.
        unique: Whether values must be unique.
        nullable: Whether NULL is allowed.
        default: Default value or callable.
        on_update: SQL expression to run on update (e.g., "NOW()").
        max_length: Maximum string length.
        min_length: Minimum string length.
        foreign_key: Foreign key reference (e.g., "departments.id").
        check: SQL CHECK constraint expression.
        index: Whether to create an index.
        comment: Column comment.
        db_type: Override auto-detected database type string.
    """

    def __init__(
        self,
        python_type: type = str,
        *,
        primary_key: bool = False,
        unique: bool = False,
        nullable: bool = True,
        default: Any = _SENTINEL,
        on_update: str | None = None,
        max_length: int | None = None,
        min_length: int | None = None,
        foreign_key: str | None = None,
        check: str | None = None,
        index: bool = False,
        comment: str | None = None,
        db_type: str | None = None,
    ) -> None:
        self.python_type = python_type
        self.primary_key = primary_key
        self.unique = unique
        self.nullable = nullable if not primary_key else False
        self.default = default
        self.on_update = on_update
        self.max_length = max_length
        self.min_length = min_length
        self.foreign_key = foreign_key
        self.check = check
        self.index = index
        self.comment = comment
        self.db_type = db_type

        # Set by Model metaclass
        self.name: str = ""
        self.field_type: FieldType = _TYPE_MAP.get(
            python_type,
            FieldType.STRING,
        )

    @property
    def has_default(self) -> bool:
        return self.default is not _SENTINEL

    def get_default(self) -> Any:
        if self.default is _SENTINEL:
            return None
        if callable(self.default):
            return self.default()
        return self.default

    def to_sql_type(self, dialect: str = "postgresql") -> str:
        """Get the SQL type string for the given dialect."""
        if self.db_type:
            return self.db_type
        return _get_sql_type(self.field_type, self.max_length, dialect)

    def validate(self, value: Any) -> list[str]:
        """Validate a value against this field's constraints."""
        errors: list[str] = []
        if value is None:
            if not self.nullable:
                errors.append(f"{self.name}: cannot be NULL")
            return errors
        if self.max_length and isinstance(value, str) and len(value) > self.max_length:
            errors.append(
                f"{self.name}: exceeds max_length {self.max_length}",
            )
        if self.min_length and isinstance(value, str) and len(value) < self.min_length:
            errors.append(
                f"{self.name}: below min_length {self.min_length}",
            )
        return errors

    def __repr__(self) -> str:
        return (
            f"Field({self.python_type.__name__}, "
            f"pk={self.primary_key}, "
            f"nullable={self.nullable})"
        )


def _get_sql_type(
    ft: FieldType,
    max_length: int | None,
    dialect: str,
) -> str:
    """Map FieldType to SQL type for a given dialect."""
    pg_map = {
        FieldType.STRING: f"VARCHAR({max_length or 255})",
        FieldType.TEXT: "TEXT",
        FieldType.INTEGER: "INTEGER",
        FieldType.BIGINT: "BIGINT",
        FieldType.FLOAT: "DOUBLE PRECISION",
        FieldType.DECIMAL: "NUMERIC",
        FieldType.BOOLEAN: "BOOLEAN",
        FieldType.DATE: "DATE",
        FieldType.DATETIME: "TIMESTAMP WITHOUT TIME ZONE",
        FieldType.TIMESTAMP: "TIMESTAMP WITH TIME ZONE",
        FieldType.UUID: "UUID",
        FieldType.JSON: "JSON",
        FieldType.JSONB: "JSONB",
        FieldType.BINARY: "BYTEA",
        FieldType.ARRAY: "TEXT[]",
    }
    mysql_map = {
        FieldType.STRING: f"VARCHAR({max_length or 255})",
        FieldType.TEXT: "TEXT",
        FieldType.INTEGER: "INT",
        FieldType.BIGINT: "BIGINT",
        FieldType.FLOAT: "DOUBLE",
        FieldType.DECIMAL: "DECIMAL",
        FieldType.BOOLEAN: "TINYINT(1)",
        FieldType.DATE: "DATE",
        FieldType.DATETIME: "DATETIME",
        FieldType.TIMESTAMP: "TIMESTAMP",
        FieldType.UUID: "CHAR(36)",
        FieldType.JSON: "JSON",
        FieldType.JSONB: "JSON",
        FieldType.BINARY: "BLOB",
        FieldType.ARRAY: "JSON",
    }
    sqlite_map = {
        FieldType.STRING: "TEXT",
        FieldType.TEXT: "TEXT",
        FieldType.INTEGER: "INTEGER",
        FieldType.BIGINT: "INTEGER",
        FieldType.FLOAT: "REAL",
        FieldType.DECIMAL: "REAL",
        FieldType.BOOLEAN: "INTEGER",
        FieldType.DATE: "TEXT",
        FieldType.DATETIME: "TEXT",
        FieldType.TIMESTAMP: "TEXT",
        FieldType.UUID: "TEXT",
        FieldType.JSON: "TEXT",
        FieldType.JSONB: "TEXT",
        FieldType.BINARY: "BLOB",
        FieldType.ARRAY: "TEXT",
    }
    type_map = {
        "postgresql": pg_map,
        "mysql": mysql_map,
        "sqlite": sqlite_map,
    }
    d = type_map.get(dialect, pg_map)
    return d.get(ft, "TEXT")


# ------------------------------------------------------------------
# Index & Constraint Descriptors
# ------------------------------------------------------------------


@dataclass
class Index:
    """Database index descriptor."""

    name: str
    columns: str | list[str] = ""
    unique: bool = False
    condition: str | None = None  # Partial index WHERE clause

    def __post_init__(self) -> None:
        if isinstance(self.columns, str):
            self.columns = [self.columns]

    def to_sql(self, table: str, dialect: str = "postgresql") -> str:
        unique = "UNIQUE " if self.unique else ""
        cols = ", ".join(self.columns)
        sql = f"CREATE {unique}INDEX {self.name} ON {table} ({cols})"
        if self.condition:
            sql += f" WHERE {self.condition}"
        return sql


@dataclass
class Constraint:
    """Database constraint descriptor."""

    name: str
    expression: str
    type: str = "CHECK"  # CHECK, UNIQUE, FOREIGN KEY

    def to_sql(self) -> str:
        return f"CONSTRAINT {self.name} {self.type} ({self.expression})"


# ------------------------------------------------------------------
# Relationship Descriptors
# ------------------------------------------------------------------


@dataclass
class HasMany:
    """One-to-many relationship descriptor."""

    target: str  # Target model/repository name
    foreign_key: str
    local_key: str = "id"


@dataclass
class BelongsTo:
    """Many-to-one relationship descriptor."""

    target: str
    foreign_key: str
    owner_key: str = "id"


@dataclass
class ManyToMany:
    """Many-to-many relationship via pivot table."""

    target: str
    pivot_table: str
    foreign_key: str
    related_key: str


# ------------------------------------------------------------------
# Model Metaclass & Base
# ------------------------------------------------------------------


class ModelMeta(type):
    """Metaclass that collects Field descriptors and configures the model."""

    def __new__(
        mcs,
        name: str,
        bases: tuple[type, ...],
        namespace: dict[str, Any],
    ) -> ModelMeta:
        fields: dict[str, Field] = {}
        relations: dict[str, HasMany | BelongsTo | ManyToMany] = {}

        # Inherit fields from bases
        for base in bases:
            if hasattr(base, "__fields__"):
                fields.update(base.__fields__)
            if hasattr(base, "__relations__"):
                relations.update(base.__relations__)

        # Collect new fields and relations
        for attr_name, attr_val in namespace.items():
            if isinstance(attr_val, Field):
                attr_val.name = attr_name
                fields[attr_name] = attr_val
            elif isinstance(attr_val, (HasMany, BelongsTo, ManyToMany)):
                relations[attr_name] = attr_val

        namespace["__fields__"] = fields
        namespace["__relations__"] = relations

        # Auto-generate tablename if not specified
        if "__tablename__" not in namespace and name != "Model":
            namespace["__tablename__"] = _to_snake_case_plural(name)

        # Process Meta class
        meta = namespace.get("Meta")
        if meta:
            namespace["__soft_delete__"] = getattr(meta, "soft_delete", False)
            namespace["__timestamps__"] = getattr(meta, "timestamps", False)
            namespace["__multi_tenant__"] = getattr(
                meta,
                "multi_tenant",
                False,
            )
            namespace["__ordering__"] = getattr(meta, "ordering", [])

        cls = super().__new__(mcs, name, bases, namespace)
        return cls


class Model(metaclass=ModelMeta):
    """Base class for declarative database models (Schema Definitions).

    In the Lexigram architecture, a `Model` represents the data-access layer
    schema mapping for a specific database table. It is distinct from an `Entity`.

    - **Entity (Domain Layer):** A pure Python object containing core business
      logic, invariants, and state, entirely agnostic of the database.
      Defined in `lexigram-contracts` or the application's domain package.
    - **Model (Infrastructure Layer):** A declarative definition of a database
      table, defining columns, indexes, and relationships. Repositories map
      between database rows (or Models) and domain Entities.

    Example:
        class UserModel(Model):
            __tablename__ = "users"

            id = Field(UUID, primary_key=True)
            email = Field(str, max_length=255, unique=True)
            name = Field(str, max_length=100)
    """

    __tablename__: str = ""
    __fields__: dict[str, Field] = {}
    __relations__: dict[str, HasMany | BelongsTo | ManyToMany] = {}
    __indexes__: list[Index] = []
    __constraints__: list[Constraint] = []

    def __init__(self, **kwargs: Any) -> None:
        for field_name, field_desc in self.__fields__.items():
            if field_name in kwargs:
                setattr(self, field_name, kwargs[field_name])
            elif field_desc.has_default:
                setattr(self, field_name, field_desc.get_default())
            else:
                setattr(self, field_name, None)

    def to_dict(self) -> dict[str, Any]:
        """Convert model instance to dictionary."""
        return {name: getattr(self, name, None) for name in self.__fields__}

    def validate(self) -> list[str]:
        """Validate all fields and return any errors."""
        errors: list[str] = []
        for name, field_desc in self.__fields__.items():
            value = getattr(self, name, None)
            errors.extend(field_desc.validate(value))
        return errors

    @classmethod
    def get_primary_key_field(cls) -> str | None:
        """Get the name of the primary key field."""
        for name, f in cls.__fields__.items():
            if f.primary_key:
                return name
        return None

    @classmethod
    def get_column_names(cls) -> list[str]:
        """Get all column names."""
        return list(cls.__fields__.keys())

    @classmethod
    def get_foreign_keys(cls) -> dict[str, str]:
        """Get all foreign key fields: {field_name: reference}."""
        return {
            name: f.foreign_key for name, f in cls.__fields__.items() if f.foreign_key
        }

    @classmethod
    def generate_create_table_sql(
        cls,
        dialect: str = "postgresql",
    ) -> str:
        """Generate CREATE TABLE SQL for this model."""
        columns: list[str] = []
        pk_cols: list[str] = []

        for name, f in cls.__fields__.items():
            parts = [name, f.to_sql_type(dialect)]
            if f.primary_key:
                pk_cols.append(name)
            if not f.nullable:
                parts.append("NOT NULL")
            if f.unique and not f.primary_key:
                parts.append("UNIQUE")
            if f.has_default and not callable(f.default):
                default_val = f.default
                if isinstance(default_val, str):
                    parts.append(f"DEFAULT '{default_val}'")
                elif isinstance(default_val, bool):
                    parts.append(
                        f"DEFAULT {'TRUE' if default_val else 'FALSE'}",
                    )
                elif default_val is not None:
                    parts.append(f"DEFAULT {default_val}")
            if f.foreign_key:
                ref_table, ref_col = f.foreign_key.split(".")
                parts.append(f"REFERENCES {ref_table}({ref_col})")
            if f.check:
                parts.append(f"CHECK ({f.check})")
            columns.append(" ".join(parts))

        if pk_cols:
            columns.append(f"PRIMARY KEY ({', '.join(pk_cols)})")

        for c in cls.__constraints__:
            columns.append(c.to_sql())

        sql = (
            f"CREATE TABLE IF NOT EXISTS {cls.__tablename__} (\n"
            f"    {(',{chr(10)}    ').join(columns)}\n"
            f")"
        )
        return sql

    def __repr__(self) -> str:
        pk_field = self.get_primary_key_field()
        pk_val = getattr(self, pk_field, "?") if pk_field else "?"
        return f"<{self.__class__.__name__} {pk_field}={pk_val}>"


def _to_snake_case_plural(name: str) -> str:
    """Convert PascalCase to snake_case_plural."""
    s = re.sub(r"(?<!^)(?=[A-Z])", "_", name).lower()
    if s.endswith("y"):
        return s[:-1] + "ies"
    if s.endswith(("s", "sh", "ch", "x", "z")):
        return s + "es"
    return s + "s"


# ------------------------------------------------------------------
# Model Lifecycle Hooks
# ------------------------------------------------------------------

# Registry for model lifecycle hooks
_model_hooks: dict[str, dict[str, list]] = {}


def _register_hook(
    model_name: str,
    event: str,
    handler: Any,
) -> None:
    """Register a lifecycle hook for a model."""
    _model_hooks.setdefault(model_name, {}).setdefault(event, []).append(
        handler,
    )


def before_create(func: Any) -> Any:
    """Decorator: called before entity creation."""
    func._hook_event = "before_create"
    return func


def after_create(func: Any) -> Any:
    """Decorator: called after entity creation."""
    func._hook_event = "after_create"
    return func


def before_update(func: Any) -> Any:
    """Decorator: called before entity update."""
    func._hook_event = "before_update"
    return func


def after_update(func: Any) -> Any:
    """Decorator: called after entity update."""
    func._hook_event = "after_update"
    return func


def before_delete(func: Any) -> Any:
    """Decorator: called before entity deletion."""
    func._hook_event = "before_delete"
    return func


def after_delete(func: Any) -> Any:
    """Decorator: called after entity deletion."""
    func._hook_event = "after_delete"
    return func


async def fire_hooks(
    model_name: str,
    event: str,
    entity: Any,
) -> None:
    """Fire all registered hooks for a model event."""
    hooks = _model_hooks.get(model_name, {}).get(event, [])
    for hook in hooks:
        import asyncio

        if asyncio.iscoroutinefunction(hook):
            await hook(entity)
        else:
            hook(entity)


__all__ = [
    "BelongsTo",
    "Constraint",
    "Field",
    "FieldType",
    "HasMany",
    "Index",
    "ManyToMany",
    "Model",
    "ModelMeta",
    "after_create",
    "after_delete",
    "after_update",
    "before_create",
    "before_delete",
    "before_update",
    "fire_hooks",
]

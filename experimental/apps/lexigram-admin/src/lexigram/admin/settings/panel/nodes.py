"""Core configuration spec and node definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
import copy
from dataclasses import MISSING
import re
from typing import TYPE_CHECKING, Any, Literal, get_args, get_origin, get_type_hints

if TYPE_CHECKING:
    from lexigram.domain import DomainModel

__all__ = [
    "AbstractConfigNode",
    "BooleanNode",
    "ColorNode",
    "ConfigSpec",
    "ConfigSpecMeta",
    "EnumNode",
    "IntNode",
    "PydanticConfigSpec",
    "SecretNode",
    "StringNode",
]

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")


class AbstractConfigNode(ABC):
    """Base class for a configuration field metadata."""

    def __init__(
        self,
        label: str,
        default: Any = None,
        help_text: str | None = None,
        required: bool = False,
        readonly: bool = False,
        icon: str | None = None,
        category: str | None = None,
        **extra,
    ) -> None:
        self.label = label
        self.default = default
        self.help_text = help_text
        self.required = required
        self.readonly = readonly
        self.icon = icon
        self.category = category
        self.extra = extra
        self._name: str | None = None

    @abstractmethod
    def validate(self, value: Any) -> Any:
        """Validate and coerce value."""

    def validation_error(self, value: Any) -> str | None:
        """Return a user-facing validation error without changing ``value``.

        ``validate`` intentionally retains its historical fallback-to-default
        behaviour because it is also used while loading legacy configuration
        values. Form submissions need a stricter, non-destructive path so a
        typo is not silently persisted as a default.
        """
        if self.required and (value is None or str(value).strip() == ""):
            return f"{self.label} is required."
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for UI rendering."""
        return {
            "name": self._name,
            "label": self.label,
            "type": self.__class__.__name__.lower().replace("node", ""),
            "default": self.default,
            "help_text": self.help_text,
            "required": self.required,
            "readonly": self.readonly,
            "icon": self.icon,
            "category": self.category,
            "extra": self.extra,
        }


class StringNode(AbstractConfigNode):
    """Configuration node for string values."""

    def validate(self, value: Any) -> str:
        """Validate and coerce value to string."""
        return str(value) if value is not None else self.default


class ColorNode(StringNode):
    """Configuration node for hex color values."""

    def validate(self, value: Any) -> str:
        """Validate value is a 6-digit hex color, else fall back to default."""
        val = str(value) if value is not None else self.default
        if not _HEX_COLOR_RE.match(val):
            return self.default
        return val

    def validation_error(self, value: Any) -> str | None:
        """Validate a color while preserving the submitted value on failure."""
        error = super().validation_error(value)
        if error:
            return error
        if not _HEX_COLOR_RE.match(str(value)):
            return (
                f"{self.label} must be a six-digit hexadecimal color, such as #6b7280."
            )
        return None


class IntNode(AbstractConfigNode):
    """Configuration node for integer values."""

    def __init__(
        self,
        label: str,
        default: Any = None,
        help_text: str | None = None,
        required: bool = False,
        readonly: bool = False,
        icon: str | None = None,
        category: str | None = None,
        ge: int | None = None,
        le: int | None = None,
        **extra,
    ) -> None:
        super().__init__(
            label,
            default=default,
            help_text=help_text,
            required=required,
            readonly=readonly,
            icon=icon,
            category=category,
            **extra,
        )
        self.ge = ge
        self.le = le

    def validate(self, value: Any) -> int:
        """Validate and coerce value to int."""
        try:
            val = int(value)
        except (ValueError, TypeError):
            return self.default
        if self.ge is not None and val < self.ge:
            return self.default
        if self.le is not None and val > self.le:
            return self.default
        return val

    def validation_error(self, value: Any) -> str | None:
        """Validate integer syntax and bounds without falling back to default."""
        error = super().validation_error(value)
        if error:
            return error
        try:
            val = int(value)
        except (ValueError, TypeError):
            return f"{self.label} must be a whole number."
        if self.ge is not None and val < self.ge:
            return f"{self.label} must be at least {self.ge}."
        if self.le is not None and val > self.le:
            return f"{self.label} must be at most {self.le}."
        return None

    def to_dict(self) -> dict[str, Any]:
        """Expose bounds so the browser can provide immediate feedback too."""
        data = super().to_dict()
        data["min"] = self.ge
        data["max"] = self.le
        return data


class BooleanNode(AbstractConfigNode):
    """Configuration node for boolean values."""

    TRUE_VALUES = frozenset({"true", "1", "yes", "on"})
    FALSE_VALUES = frozenset({"false", "0", "no", "off", ""})

    def validate(self, value: Any) -> bool:
        """Validate and coerce value to bool."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in self.TRUE_VALUES
        return bool(value)

    def validation_error(self, value: Any) -> str | None:
        """Reject ambiguous boolean payloads instead of treating them as false."""
        if isinstance(value, bool):
            return None
        if isinstance(value, str) and value.lower() in (
            self.TRUE_VALUES | self.FALSE_VALUES
        ):
            return None
        return f"{self.label} must be a boolean value."


class EnumNode(AbstractConfigNode):
    """Configuration node for enumerated choice values."""

    def __init__(
        self, *args: Any, options: list[str] | dict[str, str], **kwargs: Any
    ) -> None:
        super().__init__(*args, **kwargs)
        self.options = options

    def validate(self, value: Any) -> str:
        """Validate that value is a member of the allowed options."""
        val = str(value)
        allowed = list(self.options) if isinstance(self.options, dict) else self.options
        if val not in allowed:
            return self.default
        return val

    def validation_error(self, value: Any) -> str | None:
        """Return an error when a submitted choice is not allowed."""
        error = super().validation_error(value)
        if error:
            return error
        allowed = list(self.options) if isinstance(self.options, dict) else self.options
        if str(value) not in allowed:
            return f"{self.label} has an invalid selection."
        return None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for UI rendering, including options."""
        d = super().to_dict()
        d["options"] = self.options
        return d


class SecretNode(StringNode):
    """Field for sensitive data, usually masked in UI."""


class ConfigSpecMeta(type):
    """Metaclass to collect nodes defined on a spec."""

    def __new__(mcs, name, bases, attrs) -> Any:
        nodes: dict[str, AbstractConfigNode] = {}
        for base in bases:
            nodes.update(getattr(base, "_nodes", {}))
        for key, value in attrs.items():
            if isinstance(value, AbstractConfigNode):
                value._name = key
                nodes[key] = value

        attrs["_nodes"] = nodes
        return super().__new__(mcs, name, bases, attrs)


class ConfigSpec(metaclass=ConfigSpecMeta):
    """Base class for grouping configuration nodes."""

    namespace: str = ""
    label: str = ""
    icon: str = "cog"
    description: str = ""
    # ``required_permissions`` remains the backwards-compatible shorthand
    # for specs that use the same gate for reading and editing. New specs can
    # expose a read-only view by setting separate permissions.
    required_permissions: frozenset[str] = frozenset()
    read_permissions: frozenset[str] | None = None
    edit_permissions: frozenset[str] | None = None
    package_source: str = "built-in"
    scope: Literal["global", "tenant"] = "global"
    store_name: str = "db"
    runtime_status: Literal["active", "dormant"] = "active"

    _nodes: dict[str, AbstractConfigNode] = {}

    @classmethod
    def get_nodes(cls) -> dict[str, AbstractConfigNode]:
        """Get all nodes defined on this spec."""
        return cls._nodes

    @classmethod
    def to_dict(cls) -> dict[str, Any]:
        """Convert spec to UI-consumable format."""
        return {
            "namespace": cls.namespace,
            "label": cls.label,
            "icon": cls.icon,
            "description": cls.description,
            "scope": cls.scope,
            "store_name": cls.store_name,
            "runtime_status": cls.runtime_status,
            "required_permissions": sorted(cls.required_permissions),
            "read_permissions": sorted(
                cls.read_permissions
                if cls.read_permissions is not None
                else cls.required_permissions
            ),
            "edit_permissions": sorted(
                cls.edit_permissions
                if cls.edit_permissions is not None
                else cls.required_permissions
            ),
            "nodes": [node.to_dict() for node in cls.get_nodes().values()],
        }


class PydanticConfigSpec(ConfigSpec):
    """Spec that derives its nodes from a DomainModel.

    ``DomainModel`` is dataclass-backed (pydantic ``FieldInfo`` defaults are
    converted to ``dataclasses.field(metadata=...)`` at class creation), so
    nodes are built from ``__dataclass_fields__`` plus resolved type hints.
    """

    model: type[DomainModel] | None = None
    node_overrides: dict[str, type[AbstractConfigNode] | AbstractConfigNode] = {}

    @classmethod
    def get_nodes(cls) -> dict[str, AbstractConfigNode]:
        """Build nodes dynamically from the bound model's fields."""
        if not cls.model:
            return {}

        ensure = getattr(cls.model, "_ensure_dataclass", None)
        if callable(ensure):
            ensure(cls.model)

        dc_fields = getattr(cls.model, "__dataclass_fields__", {})
        if not dc_fields:
            raise TypeError(
                f"{cls.__name__} model must be a dataclass-backed DomainModel"
            )
        hints = getattr(cls.model, "_cached_type_hints", None)
        if not hints:
            try:
                hints = get_type_hints(cls.model)
            except (NameError, TypeError, AttributeError):
                hints = {}

        nodes: dict[str, AbstractConfigNode] = {}
        for name, field in dc_fields.items():
            annotation = hints.get(name, str)
            has_default = (
                field.default is not MISSING or field.default_factory is not MISSING
            )
            default = None if field.default is MISSING else field.default
            metadata = field.metadata or {}

            kwargs: dict[str, Any] = {
                "label": metadata.get("title") or name.replace("_", " ").title(),
                "default": default,
                "help_text": metadata.get("description"),
                "required": not has_default,
            }

            override = cls.node_overrides.get(name)
            if isinstance(override, AbstractConfigNode):
                node = copy.copy(override)
                node._name = name
                nodes[name] = node
                continue

            node_cls = override
            if node_cls is None:
                if annotation is bool:
                    node_cls = BooleanNode
                elif annotation is int:
                    node_cls = IntNode
                    kwargs["ge"] = metadata.get("ge")
                    kwargs["le"] = metadata.get("le")
                elif get_origin(annotation) is Literal:
                    node_cls = EnumNode
                    options = [str(o) for o in get_args(annotation)]
                    kwargs["options"] = options
                    if (default is None or str(default) not in options) and not kwargs[
                        "required"
                    ]:
                        kwargs["default"] = options[0]
                    if kwargs["default"] is not None:
                        kwargs["default"] = str(kwargs["default"])
                else:
                    node_cls = StringNode

            node = node_cls(**kwargs)
            node._name = name
            nodes[name] = node

        return nodes

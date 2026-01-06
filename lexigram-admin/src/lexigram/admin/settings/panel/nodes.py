"""Core configuration spec and node definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.domain import DomainModel

__all__ = [
    "AbstractConfigNode",
    "BooleanNode",
    "ConfigSpec",
    "ConfigSpecMeta",
    "EnumNode",
    "IntNode",
    "PydanticConfigSpec",
    "SecretNode",
    "StringNode",
]


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


class IntNode(AbstractConfigNode):
    """Configuration node for integer values."""

    def validate(self, value: Any) -> int:
        """Validate and coerce value to int."""
        try:
            return int(value)
        except (ValueError, TypeError):
            return self.default


class BooleanNode(AbstractConfigNode):
    """Configuration node for boolean values."""

    def validate(self, value: Any) -> bool:
        """Validate and coerce value to bool."""
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            return value.lower() in ("true", "1", "yes", "on")
        return bool(value)


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
        if isinstance(self.options, list):
            if val not in self.options:
                return self.default
        elif val not in self.options:
            return self.default
        return val

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
        nodes = {}
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
            "nodes": [node.to_dict() for node in cls.get_nodes().values()],
        }


class PydanticConfigSpec(ConfigSpec):
    """Spec that derives its nodes from a Pydantic model."""

    model: type[DomainModel] | None = None

    @classmethod
    def get_nodes(cls) -> dict[str, AbstractConfigNode]:
        """Build nodes dynamically from the bound Pydantic model's fields."""
        if not cls.model:
            return {}

        nodes: dict[str, AbstractConfigNode] = {}
        # Collect nodes from pydantic model fields
        for name, field in cls.model.model_fields.items():  # type: ignore[attr-defined]
            # Basic mapping from pydantic to ConfigNode
            node_cls: type[AbstractConfigNode] = StringNode
            annotation = field.annotation

            if annotation is int:
                node_cls = IntNode
            elif annotation is bool:
                node_cls = BooleanNode
            # Type mappings could be extended for more types in future

            node = node_cls(
                label=field.title or name.replace("_", " ").title(),
                default=field.default if field.default != ... else None,
                help_text=field.description,
                required=field.is_required(),
            )
            node._name = name
            nodes[name] = node

        return nodes

"""Core configuration spec and node definitions."""

from __future__ import annotations

from abc import ABC, abstractmethod
import copy
from dataclasses import MISSING
import json  # noqa: TID251 — form JSON parsing needs the decoder exception
import re
import types
from typing import (
    TYPE_CHECKING,
    Any,
    Literal,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)

if TYPE_CHECKING:
    from lexigram.domain import DomainModel

__all__ = [
    "AbstractConfigNode",
    "BooleanNode",
    "ColorNode",
    "ConfigSpec",
    "ConfigSpecMeta",
    "EmailNode",
    "EnumNode",
    "IntNode",
    "JsonNode",
    "PydanticConfigSpec",
    "SecretNode",
    "StringNode",
    "TimezoneNode",
    "UrlNode",
]

_HEX_COLOR_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
_EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
_BCP47_RE = re.compile(r"^[A-Za-z]{2,8}(?:-[A-Za-z0-9]{1,8})*$")


def _unwrap_optional(annotation: Any) -> Any:
    """Return the non-None member of an optional annotation when possible."""
    origin = get_origin(annotation)
    if origin in (Union, types.UnionType):
        members = tuple(
            member for member in get_args(annotation) if member is not type(None)
        )
        if len(members) == 1:
            return members[0]
    return annotation


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
    """Configuration node for string values.

    Common constraints are kept in ``extra`` so contributors can add a
    bounded/patterned string without creating a bespoke node class. ``validate``
    retains the historical fallback-to-default behavior for legacy reads;
    ``validation_error`` is the strict path used by settings POSTs.
    """

    def validate(self, value: Any) -> str | None:
        """Validate and coerce value to string, falling back when invalid."""
        text = str(value) if value is not None else self.default
        if text is None:
            return text
        if self.validation_error(text) is not None:
            return self.default
        return text

    def validation_error(self, value: Any) -> str | None:
        """Validate length, pattern, and optional semantic string formats."""
        error = super().validation_error(value)
        if error:
            return error
        text = str(value)
        minimum = self.extra.get("min_length")
        maximum = self.extra.get("max_length")
        pattern = self.extra.get("pattern")
        minimum_value = int(minimum) if minimum is not None else None
        if minimum_value is not None and minimum_value > 0 and not text.strip():
            return f"{self.label} must not be blank."
        if minimum_value is not None and len(text) < minimum_value:
            return f"{self.label} must be at least {minimum} characters."
        if maximum is not None and len(text) > int(maximum):
            return f"{self.label} must be at most {maximum} characters."
        if pattern and re.fullmatch(str(pattern), text) is None:
            return f"{self.label} has an invalid format."
        semantic_format = self.extra.get("format")
        if semantic_format == "email" and text and _EMAIL_RE.fullmatch(text) is None:
            return f"{self.label} must be a valid email address."
        if semantic_format == "url" and text:
            absolute_path = text.startswith("/") and not text.startswith("//")
            if not (absolute_path or re.match(r"^https?://[^\s]+$", text)):
                return f"{self.label} must be an HTTP(S) URL or an absolute path."
        if semantic_format == "locale" and text and _BCP47_RE.fullmatch(text) is None:
            return f"{self.label} must be a valid BCP 47 locale tag."
        return None

    def to_dict(self) -> dict[str, Any]:
        """Expose string constraints to the shared renderer."""
        data = super().to_dict()
        for key in ("min_length", "max_length", "pattern", "format", "multiline"):
            if key in self.extra:
                data[key] = self.extra[key]
        return data


class EmailNode(StringNode):
    """Configuration node for an optional or required email address."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("format", "email")
        super().__init__(*args, **kwargs)


class UrlNode(StringNode):
    """Configuration node for an HTTP(S) URL or absolute application path."""

    def __init__(self, *args: Any, **kwargs: Any) -> None:
        kwargs.setdefault("format", "url")
        super().__init__(*args, **kwargs)


class TimezoneNode(StringNode):
    """Configuration node for an IANA timezone name."""

    def validation_error(self, value: Any) -> str | None:
        """Reject names that the runtime timezone database cannot resolve."""
        error = super().validation_error(value)
        if error or not str(value).strip():
            return error
        try:
            from zoneinfo import ZoneInfo

            ZoneInfo(str(value))
        except (KeyError, TypeError, ValueError):
            return f"{self.label} must be a valid IANA timezone name."
        return None


class JsonNode(AbstractConfigNode):
    """Configuration node for JSON-encoded list, mapping, or nested values."""

    @staticmethod
    def _normalise(value: Any) -> Any:
        """Convert Python collection values to JSON-compatible containers."""
        if isinstance(value, tuple | set | frozenset):
            return list(value)
        return value

    def _matches_expected_type(self, value: Any) -> bool:
        """Check the optional collection shape derived from a model annotation."""
        expected = self.extra.get("json_type")
        if expected == "array":
            return isinstance(value, list)
        if expected == "object":
            return isinstance(value, dict)
        return True

    def validate(self, value: Any) -> Any:
        """Parse JSON form values, falling back to the declared default."""
        value = self._normalise(value)
        if isinstance(value, (dict, list)):
            return value if self._matches_expected_type(value) else self.default
        if value is None:
            return self.default
        try:
            parsed = self._normalise(json.loads(str(value)))
        except (TypeError, ValueError, json.JSONDecodeError):
            return self.default
        return parsed if self._matches_expected_type(parsed) else self.default

    def validation_error(self, value: Any) -> str | None:
        """Require valid JSON and the declared collection shape."""
        error = super().validation_error(value)
        if error:
            return error
        value = self._normalise(value)
        if isinstance(value, (dict, list)):
            parsed = value
        else:
            try:
                parsed = self._normalise(json.loads(str(value)))
            except (TypeError, ValueError, json.JSONDecodeError):
                return f"{self.label} must contain valid JSON."
        if not self._matches_expected_type(parsed):
            expected = self.extra.get("json_type")
            description = "an array" if expected == "array" else "an object"
            return f"{self.label} must contain {description}."
        return None

    def to_dict(self) -> dict[str, Any]:
        """Expose the expected JSON shape to generic form renderers."""
        data = super().to_dict()
        if "json_type" in self.extra:
            data["json_type"] = self.extra["json_type"]
        return data


class ColorNode(StringNode):
    """Configuration node for hex color values."""

    def validate(self, value: Any) -> str:
        """Validate value is a 6-digit hex color, else fall back to default."""
        val = str(value) if value is not None else self.default
        if not isinstance(val, str) or _HEX_COLOR_RE.fullmatch(val) is None:
            return self.default
        return val

    def validation_error(self, value: Any) -> str | None:
        """Validate a color while preserving the submitted value on failure."""
        error = super().validation_error(value)
        if error:
            return error
        if _HEX_COLOR_RE.fullmatch(str(value)) is None:
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

    def to_dict(self) -> dict[str, Any]:
        """Expose metadata without serializing a secret default."""
        data = super().to_dict()
        data["default"] = None
        return data


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
    runtime_status: Literal["active", "restart_required", "dormant"] = "active"

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
            annotation = _unwrap_optional(hints.get(name, str))
            has_default = (
                field.default is not MISSING or field.default_factory is not MISSING
            )
            if field.default is not MISSING:
                default = field.default
            elif field.default_factory is not MISSING:
                try:
                    default = field.default_factory()
                except Exception:  # noqa: BLE001 — metadata must remain discoverable
                    default = None
            else:
                default = None
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
                # Keep imports local so the node module remains usable in
                # deployments that do not install pydantic directly.
                secret_type: Any = ()
                try:
                    from lexigram.validation import SecretStr

                    secret_type = SecretStr
                except ImportError:  # pragma: no cover - workspace always has it
                    pass

                origin = get_origin(annotation)
                if annotation is bool:
                    node_cls = BooleanNode
                elif annotation is int:
                    node_cls = IntNode
                    kwargs["ge"] = metadata.get("ge")
                    kwargs["le"] = metadata.get("le")
                elif annotation is secret_type:
                    node_cls = SecretNode
                elif origin is Literal:
                    node_cls = EnumNode
                    options = [str(o) for o in get_args(annotation)]
                    kwargs["options"] = options
                    if (default is None or str(default) not in options) and not kwargs[
                        "required"
                    ]:
                        kwargs["default"] = options[0]
                    if kwargs["default"] is not None:
                        kwargs["default"] = str(kwargs["default"])
                elif origin in (list, tuple, dict, set):
                    node_cls = JsonNode
                    # JSON is easier to inspect and edit safely than a
                    # Python repr, and the validator returns the parsed type.
                    kwargs["multiline"] = True
                    kwargs["json_type"] = "object" if origin is dict else "array"
                elif isinstance(annotation, type) and hasattr(
                    annotation, "__dataclass_fields__"
                ):
                    node_cls = JsonNode
                    kwargs["multiline"] = True
                    kwargs["json_type"] = "object"
                else:
                    node_cls = StringNode

            # Model constraints remain part of the contract even when a
            # contributor selects a semantic override such as EmailNode,
            # UrlNode, or TimezoneNode. This also lets an IntNode override
            # retain its declared numeric bounds.
            if isinstance(node_cls, type) and issubclass(node_cls, IntNode):
                for key in ("ge", "le"):
                    if key in metadata:
                        kwargs.setdefault(key, metadata[key])
            for key in ("min_length", "max_length", "pattern"):
                if key in metadata:
                    kwargs.setdefault(key, metadata[key])

            node = node_cls(**kwargs)
            node._name = name
            nodes[name] = node

        return nodes

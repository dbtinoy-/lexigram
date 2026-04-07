from __future__ import annotations

from abc import ABC, abstractmethod
import copy
from dataclasses import dataclass, field
from enum import StrEnum
from typing import TYPE_CHECKING, Any, Self

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from collections.abc import Callable

    from lexigram.ui.core.base import Component

logger = get_logger(__name__)


class FieldType(StrEnum):
    """Supported form field types."""

    TEXT = "text"
    NUMBER = "number"
    EMAIL = "email"
    PASSWORD = "password"
    CHECKBOX = "checkbox"
    SELECT = "select"
    MULTI_SELECT = "multi_select"
    DATE = "date"
    DATETIME = "datetime"
    TEXTAREA = "textarea"
    FILE = "file"
    IMAGE = "image"
    NESTED = "nested"
    LIST = "list"
    RICH_TEXT = "rich_text"
    MARKDOWN = "markdown"
    COLOR = "color"
    TAGS = "tags"
    KEY_VALUE = "key_value"
    JSON = "json"
    BELONGS_TO = "belongs_to"
    HAS_MANY = "has_many"
    MORPH = "morph"


@dataclass
class FieldSchema:
    """Definition of a single form field schema."""

    name: str
    label: str
    type: FieldType = FieldType.TEXT
    required: bool = False
    default: Any = None
    placeholder: str | None = None
    help_text: str | None = None
    options: list[dict[str, Any]] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    nested_schema: Any | None = None  # Avoid circular with FormSchema
    validation: dict[str, Any] = field(default_factory=dict)
    visible: bool = True
    editable: bool = True
    masked: bool = False
    related_resource: str | None = None
    """Name of the related admin resource (e.g. 'users', 'pets')."""
    related_field: str | None = None
    """The FK field name on the related side (for HAS_MANY)."""


class Block:
    """Definition of a content block for the Builder component."""

    def __init__(
        self,
        name: str,
        fields: list[Any],
        label: str | None = None,
        icon: str | None = None,
    ):
        self.name = name
        self.fields = fields
        self.label = label or name.replace("_", " ").title()
        self.icon = icon


class AdminField:
    """Metadata for a Pydantic field to control how it's rendered in the admin UI."""

    def __init__(
        self,
        label: str | None = None,
        widget: type | None = None,
        help_text: str | None = None,
        belongs_to: str | None = None,
        belongs_to_many: str | None = None,
        searchable: bool = False,
        email: bool = False,
        url: bool = False,
        min_value: int | None = None,
        max_value: int | None = None,
        regex: str | None = None,
        unique: bool = False,
        confirmed: bool = False,
        **props: Any,
    ):
        self._label = label
        self._widget = widget
        self._help_text = help_text
        self._belongs_to = belongs_to
        self._belongs_to_many = belongs_to_many
        self._searchable = searchable
        self.email = email
        self.url = url
        self.min = min_value
        self.max = max_value
        self.regex = regex
        self._unique = unique
        self.confirmed = confirmed
        self._placeholder: str | None = None
        self._default_value: Any = None
        self._disabled = False
        self._readonly = False
        self._hidden = False
        self._visible_condition: Callable[[dict], bool] | None = None
        self._hint: str | None = None
        self._props = props

    def label(self, value: str) -> Self:
        self._label = value
        return self

    def widget(self, value: type) -> Self:
        self._widget = value
        return self

    def props(self, **kwargs: Any) -> Self:
        self._props.update(kwargs)
        return self

    def help_text(self, value: str) -> Self:
        self._help_text = value
        return self

    def placeholder(self, value: str) -> Self:
        self._placeholder = value
        return self

    def default(self, value: Any) -> Self:
        self._default_value = value
        return self

    def disabled(self, value: bool = True) -> Self:
        self._disabled = value
        return self

    def readonly(self, value: bool = True) -> Self:
        self._readonly = value
        return self

    def hidden(self, value: bool = True) -> Self:
        self._hidden = value
        return self

    def visible(self, condition: Callable[[dict], bool]) -> Self:
        self._visible_condition = condition
        return self

    def visible_when(self, expression: str) -> Self:
        self._props["visible_when"] = expression
        return self

    def hint(self, text: str) -> Self:
        self._hint = text
        return self

    def searchable(self, value: bool = True) -> Self:
        self._searchable = value
        return self

    def builder(self, blocks: list[Block]) -> Self:
        self._props["builder_blocks"] = blocks
        self._widget = "Builder"  # type: ignore[assignment]
        return self

    def prefix(self, text: str) -> Self:
        self._props["prefix"] = text
        return self

    def suffix(self, text: str) -> Self:
        self._props["suffix"] = text
        return self

    def mask(self, pattern: str) -> Self:
        self._props["mask"] = pattern
        return self

    def currency(self, code: str = "USD") -> Self:
        self._props["currency"] = code
        return self

    def format_state_using(self, callback: Callable[[Any], Any]) -> Self:
        self._props["format_state_using"] = callback
        return self

    def dehydrate_state_using(self, callback: Callable[[Any], Any]) -> Self:
        self._props["dehydrate_state_using"] = callback
        return self

    def prefill_from(
        self,
        field_name: str,
        transformer_js: str | None = None,
    ) -> Self:
        self._props["prefill_from"] = field_name
        self._props["prefill_transformer"] = transformer_js
        return self

    def __call__(self, label: str) -> Self:
        self._label = label
        return self


class AbstractField(ABC):
    """Abstract base class for all form fields."""

    def __init__(
        self,
        label: str | None = None,
        required: bool = True,
        disabled: bool = False,
        help_text: str | None = None,
        default: Any = None,
        placeholder: str | None = None,
        validators: list[Callable] | None = None,
        name: str | None = None,
        realtime_validate: bool = False,
        async_validate: Callable[[Any], Any] | None = None,
        format_state_using: Callable[[Any], Any] | None = None,
        dehydrate_state_using: Callable[[Any], Any] | None = None,
        autocomplete_source: str | Callable[[], list[str]] | None = None,
        mask_pattern: str | None = None,
        prefix: str | None = None,
        suffix: str | None = None,
        currency: str | None = None,
        decimals: int | None = None,
        prefill_from: str | None = None,
    ):
        self.label = label
        self.required = required
        self.disabled = disabled
        self.help_text = help_text
        self.default = default
        self.placeholder = placeholder
        self.validators = validators or []
        self._name = name
        self.realtime_validate = realtime_validate
        self.async_validator = async_validate
        self.format_state_using = format_state_using
        self.dehydrate_state_using = dehydrate_state_using
        self.autocomplete_source = autocomplete_source
        self.mask_pattern = mask_pattern
        self.prefix = prefix
        self.suffix = suffix
        self._currency = currency
        self.decimals = decimals
        self.prefill_from = prefill_from
        self.aria_label = label
        self.aria_describedby = f"{self.name}-help" if help_text else None
        self.aria_errormessage = f"{self.name}-error"
        self.value: Any = default
        self.errors: list[str] = []
        self.is_bound = False
        self.is_validating = False

    def get_default(self) -> Any:
        """Return the default value for this field."""
        return self.default

    @property
    def name(self) -> str:
        return self._name or "unnamed_field"

    @name.setter
    def name(self, value: str) -> Any:
        self._name = value

    def bind(self, value: Any) -> AbstractField:
        new_field = copy.copy(self)
        new_field.value = value if value is not None else self.default
        new_field.is_bound = True
        return new_field

    def validate(self, value: Any) -> Any:
        if self.required and value in (None, ""):
            raise ValueError(f"{self.label or self.name} is required")
        return value

    async def run_async_validation(self, value: Any) -> Any:
        if self.async_validator:
            try:
                self.is_validating = True
                result = await self.async_validator(value)
                self.is_validating = False
                return result
            except Exception as e:  # noqa: BLE001 — async validators are user-supplied callables that may raise anything
                self.is_validating = False
                logger.exception("Async validator failed for field %s", self._name)
                raise ValueError(str(e)) from None
        return value

    def format_value(self, value: Any) -> Any:
        if self.format_state_using:
            try:
                return self.format_state_using(value)
            except BaseException:
                logger.exception("Custom formatter failed for field %s", self._name)
        return value

    def dehydrate_value(self, value: Any) -> Any:
        if self.dehydrate_state_using:
            try:
                return self.dehydrate_state_using(value)
            except BaseException:
                logger.exception("Custom dehydrator failed for field %s", self._name)
        return value

    def apply_mask(self, value: str) -> str:
        if not self.mask_pattern or not value:
            return value
        masked = ""
        value_idx = 0
        for char in self.mask_pattern:
            if char == "#" and value_idx < len(value):
                if value[value_idx].isdigit():
                    masked += value[value_idx]
                    value_idx += 1
                else:
                    break
            elif char != "#" and value_idx < len(value):
                masked += char
                if value[value_idx] == char:
                    value_idx += 1
            elif char != "#":
                masked += char
        return masked

    @abstractmethod
    def render(self, **kwargs) -> Component:
        pass

    def render_with_conditional(self, **kwargs) -> Any:
        """Render the field, wrapped in an Alpine x-show div when ``visible_when`` is set.

        This is the preferred call site when rendering fields inside a
        ``FormBase`` or ``LayoutNode``, as it transparently adds the
        ``x-show`` / ``x-cloak`` attributes required for declarative
        show/hide based on other field values.
        """
        from lexigram.ui.core.base import el as _el

        rendered = self.render(**kwargs)
        expr = getattr(self, "_visible_expression", None)
        if expr:
            return _el("div", rendered, **{"x-show": expr, "x-cloak": True})
        return rendered

    def visible_when(self, expression: str) -> AbstractField:
        """Declare a client-side Alpine.js condition controlling visibility.

        Args:
            expression: An Alpine.js boolean expression evaluated in the form
                context, e.g. ``"formData.type === 'premium'"``.

        Returns:
            Self for method chaining.
        """
        self._visible_expression = expression
        return self

    def is_visible(self, form_data: dict[str, Any]) -> bool:
        """Server-side visibility check (Python-evaluated).

        For client-side (Alpine.js) show/hide use :meth:`visible_when`.
        """
        return True


# Backward-compatible public symbol expected by field modules/importers.
Field = AbstractField

"""Form builder with Pydantic integration.

Provides a declarative API for building forms from Pydantic models
with automatic validation, HTMX integration, and customization.

The built ``Form`` object and ``FormResult`` live in ``form`` and are
re-exported here.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import date, datetime
from enum import Enum
from typing import (
    TYPE_CHECKING,
    Any,
    Generic,
    TypeVar,
    Union,
    get_args,
    get_origin,
    get_type_hints,
)
import types


from lexigram.admin.forms.form import (
    Form as Form,
)
from lexigram.admin.forms.form import (
    FormResult as FormResult,
)
from lexigram.admin.schema import (
    BooleanField,
    DateField,
    DateTimeField,
    EmailField,
    EnumField,
    IntegerField,
    MultiSelectField,
    PasswordField,
    SchemaField,
    SelectField,
    TextAreaField,
    TextField,
)
from lexigram.domain import DomainModel
from lexigram.logging import get_logger
from lexigram.primitives.builder import AbstractBuilder

if TYPE_CHECKING:
    from collections.abc import Callable

logger = get_logger(__name__)

T = TypeVar("T", bound=DomainModel)


@dataclass
class FieldConfig:
    """Configuration for a form field."""

    name: str
    label: str | None = None
    help_text: str | None = None
    placeholder: str | None = None
    required: bool = True
    disabled: bool = False
    hidden: bool = False
    widget: str | None = None  # Override default widget
    order: int = 100
    group: str | None = None
    col_span: int = 1  # For grid layouts
    validators: list[Callable] = dataclass_field(default_factory=list)
    props: dict[str, Any] = dataclass_field(default_factory=dict)


class FormBuilder(AbstractBuilder["Form[T]"], Generic[T]):
    """Build forms from Pydantic models.

    Usage:
        @dataclass(init=False)
        class UserForm(DomainModel):
            name: str
            email: str
            age: int

        form = (FormBuilder(UserForm)
            .field("name", label="Full Name", placeholder="Enter your name")
            .field("email", widget="email")
            .field("age", help_text="Must be 18 or older")
            .exclude("password")
            .build())
    """

    def __init__(self, model: type[T]):
        super().__init__()
        self.model = model
        self._field_configs: dict[str, FieldConfig] = {}
        self._excluded: set[str] = set()
        self._groups: dict[str, list[str]] = {}
        self._group_labels: dict[str, str] = {}
        self._layout: str = "vertical"  # "vertical", "horizontal", "grid"
        self._columns: int = 1
        self._submit_label: str = "Submit"
        self._cancel_url: str | None = None

        self._form_class: type | None = None

        # Extract fields from model
        self._init_from_model()

    def _init_from_model(self) -> None:
        """Initialize field configs from Pydantic model."""
        hints = get_type_hints(self.model)
        model_fields = self.model.model_fields  # type: ignore[attr-defined]

        for name, field_info in model_fields.items():
            hints.get(name, str)

            # Determine if required
            required = field_info.is_required()

            # Generate label from name
            label = name.replace("_", " ").title()

            # Get help text from description
            help_text = field_info.description

            # Determine default

            self._field_configs[name] = FieldConfig(
                name=name,
                label=label,
                help_text=help_text,
                required=required,
            )

    def field(
        self,
        name: str,
        *,
        label: str | None = None,
        help_text: str | None = None,
        placeholder: str | None = None,
        required: bool | None = None,
        disabled: bool = False,
        hidden: bool = False,
        widget: str | None = None,
        order: int | None = None,
        group: str | None = None,
        col_span: int = 1,
        validators: list[Callable] | None = None,
        **props: Any,
    ) -> FormBuilder[T]:
        """Configure a field."""
        if name not in self._field_configs:
            raise ValueError(f"Unknown field: {name}")

        config = self._field_configs[name]

        if label is not None:
            config.label = label
        if help_text is not None:
            config.help_text = help_text
        if placeholder is not None:
            config.placeholder = placeholder
        if required is not None:
            config.required = required
        if disabled:
            config.disabled = disabled
        if hidden:
            config.hidden = hidden
        if widget is not None:
            config.widget = widget
        if order is not None:
            config.order = order
        if group is not None:
            config.group = group
            if group not in self._groups:
                self._groups[group] = []
            if name not in self._groups[group]:
                self._groups[group].append(name)
        if validators:
            config.validators.extend(validators)

        config.col_span = col_span
        config.props.update(props)

        return self

    def exclude(self, *fields: str) -> FormBuilder[T]:
        """Exclude fields from the form."""
        self._excluded.update(fields)
        return self

    def include_only(self, *fields: str) -> FormBuilder[T]:
        """Include only specified fields."""
        all_fields = set(self._field_configs.keys())
        self._excluded = all_fields - set(fields)
        return self

    def group(
        self,
        name: str,
        *fields: str,
        label: str | None = None,
    ) -> FormBuilder[T]:
        """Group fields together."""
        self._groups[name] = list(fields)
        if label is not None:
            self._group_labels[name] = label
        for field_name in fields:
            if field_name in self._field_configs:
                self._field_configs[field_name].group = name
        return self

    def layout(self, layout: str, columns: int = 1) -> FormBuilder[T]:
        """Set form layout."""
        self._layout = layout
        self._columns = columns
        return self

    def submit_label(self, label: str) -> FormBuilder[T]:
        """Set submit button label."""
        self._submit_label = label
        return self

    def cancel_url(self, url: str) -> FormBuilder[T]:
        """Set cancel button URL."""
        self._cancel_url = url
        return self

    @classmethod
    def create(cls, form_class: type | None = None) -> FormBuilder:
        """Create a fluent FormBuilder without a Pydantic model.

        Supports the create()/text()/build() API for lightweight dynamic forms.
        """
        builder: FormBuilder = cls.__new__(cls)
        super(FormBuilder, builder).__init__()
        builder.model = None  # type: ignore[assignment]
        builder._field_configs = {}
        builder._excluded = set()
        builder._groups = {}
        builder._group_labels = {}
        builder._layout = "vertical"
        builder._columns = 1
        builder._submit_label = "Submit"
        builder._cancel_url = None
        builder._form_class = form_class
        return builder

    def text(self, name: str, **kwargs: Any) -> FormBuilder[T]:
        """Add a text field to the form (fluent API)."""
        label: str = kwargs.get("label") or name.replace("_", " ").title()
        self._field_configs[name] = FieldConfig(
            name=name,
            label=label,
            help_text=kwargs.get("help_text"),
            placeholder=kwargs.get("placeholder"),
            required=kwargs.get("required", True),
        )
        return self

    def build(self) -> Form[T]:
        """Build the form."""
        fields: list[SchemaField] = []
        hints = get_type_hints(self.model) if self.model is not None else {}

        # Sort by order
        sorted_configs = sorted(self._field_configs.items(), key=lambda x: x[1].order)

        for name, config in sorted_configs:
            if name in self._excluded or config.hidden:
                continue

            field_type = hints.get(name, str)
            field = self._create_field(name, field_type, config)
            fields.append(field)

        return Form(
            model=self.model,
            fields=fields,
            groups=self._groups,
            group_labels=self._group_labels,
            layout=self._layout,
            columns=self._columns,
            submit_label=self._submit_label,
            cancel_url=self._cancel_url,
        )

    def _create_field(
        self,
        name: str,
        field_type: type,
        config: FieldConfig,
    ) -> SchemaField:
        """Create a SchemaField instance from type and config."""
        # Handle widget override
        if config.widget:
            return self._create_field_by_widget(name, config)

        # Handle Optional types
        origin = get_origin(field_type)
        if origin in (Union, types.UnionType):
            args = get_args(field_type)
            # Get the non-None type while retaining the builder's explicit
            # required override when one was supplied.
            for arg in args:
                if arg is not type(None):
                    field_type = arg
                    if not config.required:
                        config.required = False
                    break

        common: dict[str, Any] = {
            "name": name,
            "label": config.label,
            "help_text": config.help_text,
            "required": config.required,
            "readonly": config.disabled,
            "placeholder": config.placeholder,
            "validators": list(config.validators),
        }

        # Map Python types to schema field classes
        if get_origin(field_type) is list:
            args = get_args(field_type)
            options = config.props.get("options", [])
            return MultiSelectField(**common, options=options)
        if field_type is str:
            return TextField(**common)
        if field_type is int:
            return IntegerField(**common)
        if field_type is bool:
            return BooleanField(**common)
        if field_type is date:
            return DateField(**common)
        if field_type is datetime:
            return DateTimeField(**common)
        if isinstance(field_type, type) and issubclass(field_type, Enum):
            return EnumField(
                **common,
                enum_cls=field_type,
            )
        # Default to text
        return TextField(**common)

    def _create_field_by_widget(self, name: str, config: FieldConfig) -> SchemaField:
        """Create field by widget name."""
        widget = config.widget
        common: dict[str, Any] = {
            "name": name,
            "label": config.label,
            "help_text": config.help_text,
            "required": config.required,
            "readonly": config.disabled,
            "placeholder": config.placeholder,
            "validators": list(config.validators),
        }
        if widget == "textarea":
            return TextAreaField(**common)
        if widget == "email":
            return EmailField(**common)
        if widget == "password":
            return PasswordField(**common)
        if widget == "switch":
            return BooleanField(**common)
        if widget == "select":
            options = config.props.get("options", [])
            return SelectField(**common, options=options)
        if widget in {"multi_select", "multiselect"}:
            options = config.props.get("options", [])
            return MultiSelectField(**common, options=options)
        return TextField(**common)

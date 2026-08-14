from __future__ import annotations

from lexigram.admin.openapi.field_converter import field_to_openapi_property
from lexigram.admin.schema import (
    BooleanField,
    ColorField,
    CurrencyField,
    DateField,
    DateTimeField,
    EmailField,
    FileField,
    FloatField,
    HiddenField,
    ImageField,
    IntegerField,
    JsonField,
    KeyValueField,
    MarkdownField,
    MultiSelectField,
    NumberField,
    PasswordField,
    RadioField,
    RatingField,
    RichTextField,
    SelectField,
    TagsField,
    TextAreaField,
    TextField,
    TimeField,
    ToggleField,
    URLField,
)
from lexigram.admin.schema.relation import (
    BelongsToField,
    HasManyField,
    MorphField,
    RelationField,
)
from lexigram.admin.schema.validators import (
    LengthValidator,
    PatternValidator,
    RangeValidator,
    RequiredValidator,
)


class TestTextField:
    def test_text(self) -> None:
        field = TextField(name="name")
        assert field_to_openapi_property(field) == {"type": "string"}

    def test_email(self) -> None:
        field = EmailField(name="email")
        assert field_to_openapi_property(field) == {
            "type": "string",
            "format": "email",
        }

    def test_password(self) -> None:
        field = PasswordField(name="password")
        assert field_to_openapi_property(field) == {
            "type": "string",
            "format": "password",
        }

    def test_url(self) -> None:
        field = URLField(name="url")
        assert field_to_openapi_property(field) == {
            "type": "string",
            "format": "uri",
        }

    def test_textarea(self) -> None:
        field = TextAreaField(name="bio")
        assert field_to_openapi_property(field) == {"type": "string"}

    def test_markdown(self) -> None:
        field = MarkdownField(name="content")
        assert field_to_openapi_property(field) == {"type": "string"}

    def test_richtext(self) -> None:
        field = RichTextField(name="body")
        assert field_to_openapi_property(field) == {"type": "string"}

    def test_color(self) -> None:
        field = ColorField(name="theme")
        assert field_to_openapi_property(field) == {"type": "string"}

    def test_hidden(self) -> None:
        field = HiddenField(name="token")
        assert field_to_openapi_property(field) == {"type": "string"}


class TestNumericField:
    def test_integer(self) -> None:
        field = IntegerField(name="age")
        assert field_to_openapi_property(field) == {
            "type": "integer",
            "format": "int32",
        }

    def test_float(self) -> None:
        field = FloatField(name="price")
        assert field_to_openapi_property(field) == {
            "type": "number",
            "format": "float",
        }

    def test_currency(self) -> None:
        field = CurrencyField(name="amount")
        assert field_to_openapi_property(field) == {"type": "number"}

    def test_number(self) -> None:
        field = NumberField(name="rating")
        assert field_to_openapi_property(field) == {"type": "number"}

    def test_rating(self) -> None:
        field = RatingField(name="stars")
        assert field_to_openapi_property(field) == {
            "type": "integer",
            "minimum": 1,
            "maximum": 5,
        }


class TestBooleanField:
    def test_boolean(self) -> None:
        field = BooleanField(name="active")
        assert field_to_openapi_property(field) == {"type": "boolean"}

    def test_toggle(self) -> None:
        field = ToggleField(name="enabled")
        assert field_to_openapi_property(field) == {"type": "boolean"}


class TestDateTimeField:
    def test_date(self) -> None:
        field = DateField(name="birth_date")
        assert field_to_openapi_property(field) == {
            "type": "string",
            "format": "date",
        }

    def test_datetime(self) -> None:
        field = DateTimeField(name="created_at")
        assert field_to_openapi_property(field) == {
            "type": "string",
            "format": "date-time",
        }

    def test_time(self) -> None:
        field = TimeField(name="start_time")
        assert field_to_openapi_property(field) == {
            "type": "string",
            "format": "time",
        }


class TestSelectField:
    def test_select(self) -> None:
        field = SelectField(
            name="role",
            options=[("admin", "Admin"), ("user", "User")],
        )
        assert field_to_openapi_property(field) == {
            "type": "string",
            "enum": ["admin", "user"],
        }

    def test_select_no_options(self) -> None:
        field = SelectField(name="role", options=[])
        assert field_to_openapi_property(field) == {"type": "string"}

    def test_radio(self) -> None:
        field = RadioField(
            name="color",
            options=[("red", "Red"), ("blue", "Blue")],
        )
        assert field_to_openapi_property(field) == {
            "type": "string",
            "enum": ["red", "blue"],
        }

    def test_multi_select(self) -> None:
        field = MultiSelectField(
            name="tags",
            options=[("a", "A"), ("b", "B")],
        )
        assert field_to_openapi_property(field) == {
            "type": "array",
            "items": {"type": "string", "enum": ["a", "b"]},
        }

    def test_tags(self) -> None:
        field = TagsField(name="keywords")
        assert field_to_openapi_property(field) == {
            "type": "array",
            "items": {"type": "string"},
        }


class TestRelationField:
    def test_relation(self) -> None:
        field = RelationField(name="user_id", resource="users")
        assert field_to_openapi_property(field) == {"type": "string"}

    def test_belongs_to(self) -> None:
        field = BelongsToField(name="author_id", resource="users")
        assert field_to_openapi_property(field) == {"type": "string"}

    def test_has_many(self) -> None:
        field = HasManyField(
            name="tag_ids",
            resource="tags",
            options=[("1", "Tag 1"), ("2", "Tag 2")],
        )
        assert field_to_openapi_property(field) == {
            "type": "array",
            "items": {"type": "string", "enum": ["1", "2"]},
        }

    def test_morph(self) -> None:
        field = MorphField(name="taggable", resource="*")
        assert field_to_openapi_property(field) == {"type": "string"}


class TestComplexField:
    def test_json(self) -> None:
        field = JsonField(name="metadata")
        assert field_to_openapi_property(field) == {"type": "object"}

    def test_key_value(self) -> None:
        field = KeyValueField(name="attributes")
        assert field_to_openapi_property(field) == {
            "type": "object",
            "additionalProperties": {"type": "string"},
        }


class TestFileField:
    def test_file(self) -> None:
        field = FileField(name="attachment")
        assert field_to_openapi_property(field) == {
            "type": "string",
            "format": "binary",
        }

    def test_image(self) -> None:
        field = ImageField(name="avatar")
        assert field_to_openapi_property(field) == {
            "type": "string",
            "format": "binary",
        }


class TestModifiers:
    def test_nullable(self) -> None:
        """Default nullable=True means the property doesn't get a nullable key
        (only non-nullable fields explicitly include nullable: False)."""
        field = TextField(name="name", nullable=True)
        assert "nullable" not in field_to_openapi_property(field)

    def test_non_nullable(self) -> None:
        field = TextField(name="name", nullable=False)
        assert field_to_openapi_property(field)["nullable"] is False

    def test_readonly(self) -> None:
        field = TextField(name="name", readonly=True)
        assert field_to_openapi_property(field)["readOnly"] is True

    def test_default(self) -> None:
        field = TextField(name="name", default="default_name")
        assert field_to_openapi_property(field)["default"] == "default_name"

    def test_help_text(self) -> None:
        field = TextField(name="name", help_text="The user's full name")
        prop = field_to_openapi_property(field)
        assert prop["description"] == "The user's full name"


class TestValidatorConstraints:
    def test_length_min(self) -> None:
        field = TextField(name="name", validators=[LengthValidator(min_length=3)])
        prop = field_to_openapi_property(field)
        assert prop["minLength"] == 3

    def test_length_max(self) -> None:
        field = TextField(name="name", validators=[LengthValidator(max_length=100)])
        prop = field_to_openapi_property(field)
        assert prop["maxLength"] == 100

    def test_length_both(self) -> None:
        field = TextField(
            name="name",
            validators=[LengthValidator(min_length=3, max_length=100)],
        )
        prop = field_to_openapi_property(field)
        assert prop["minLength"] == 3
        assert prop["maxLength"] == 100

    def test_range_min(self) -> None:
        field = IntegerField(name="age", validators=[RangeValidator(min_value=0)])
        prop = field_to_openapi_property(field)
        assert prop["minimum"] == 0

    def test_range_max(self) -> None:
        field = IntegerField(name="age", validators=[RangeValidator(max_value=150)])
        prop = field_to_openapi_property(field)
        assert prop["maximum"] == 150

    def test_pattern(self) -> None:
        field = TextField(
            name="code",
            validators=[PatternValidator(r"^[A-Z]{3}\d{3}$")],
        )
        prop = field_to_openapi_property(field)
        assert prop["pattern"] == r"^[A-Z]{3}\d{3}$"

    def test_required_validator_no_constraint(self) -> None:
        field = TextField(name="name", validators=[RequiredValidator()])
        prop = field_to_openapi_property(field)
        assert "minLength" not in prop
        assert "pattern" not in prop

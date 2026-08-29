"""Unit tests for the new Form System."""

from dataclasses import dataclass, field

import pytest

from lexigram.admin.forms import (
    FormLayoutBuilder,
    FormSchemaGenerator,
    FormStore,
    FormValidationEngine,
    email,
    required,
)
from lexigram.admin.schema import (
    BelongsToField,
    BooleanField,
    HasManyField,
    JsonField,
    MorphField,
    MultiSelectField,
    TextField,
)
from lexigram.domain import DomainModel
from lexigram.validation import Field


@dataclass
class UserProfile(DomainModel):
    bio: str
    age: int


@dataclass
class Pet(DomainModel):
    name: str
    species: str


@dataclass
class Role(DomainModel):
    name: str


@dataclass
class Permission(DomainModel):
    name: str


@dataclass
class User(DomainModel):
    username: str = Field(..., title="Username", description="Unique name")
    email: str
    is_active: bool = True
    profile: UserProfile | None = None
    tags: list[str] = field(default_factory=list)
    owner_id: str | None = None
    pets: list[Pet] = field(default_factory=list)


@dataclass
class PolymorphicModel(DomainModel):
    name: str
    target: Role | Permission | None = None


class TestFormSchemaGenerator:
    def test_from_pydantic_simple(self):
        gen = FormSchemaGenerator()
        schema = gen.from_pydantic(User)

        assert schema.title == "User"
        assert len(schema.fields) == 7

        username_field = schema.get_field("username")
        assert isinstance(username_field, TextField)
        assert username_field.label == "Username"
        assert username_field.required is True
        assert username_field.help_text == "Unique name"

        email_field = schema.get_field("email")
        assert isinstance(email_field, TextField)

        active_field = schema.get_field("is_active")
        assert isinstance(active_field, BooleanField)
        assert active_field.default is True

    def test_from_pydantic_nested(self):
        gen = FormSchemaGenerator()
        schema = gen.from_pydantic(User)

        profile_field = schema.get_field("profile")
        assert isinstance(profile_field, JsonField)

        tags_field = schema.get_field("tags")
        assert isinstance(tags_field, MultiSelectField)

    def test_detects_belongs_to_fk(self):
        gen = FormSchemaGenerator()
        schema = gen.from_pydantic(User)

        owner_field = schema.get_field("owner_id")
        assert owner_field is not None
        assert isinstance(owner_field, BelongsToField)
        assert owner_field.resource == "owners"

    def test_detects_has_many(self):
        gen = FormSchemaGenerator()
        schema = gen.from_pydantic(User)

        pets_field = schema.get_field("pets")
        assert pets_field is not None
        assert isinstance(pets_field, HasManyField)
        assert pets_field.resource == "pets"

    def test_detects_morph(self):
        gen = FormSchemaGenerator()
        schema = gen.from_pydantic(PolymorphicModel)

        target_field = schema.get_field("target")
        assert target_field is not None
        assert isinstance(target_field, MorphField)

    def test_plain_str_id_not_detected_as_fk(self):
        @dataclass
        class Plain(DomainModel):
            identifier: str

        gen = FormSchemaGenerator()
        schema = gen.from_pydantic(Plain)
        field = schema.get_field("identifier")
        assert isinstance(field, TextField)

    def test_resource_registry_accepted(self):
        gen = FormSchemaGenerator(resource_registry={"users": User})
        assert gen.resource_registry == {"users": User}

    def test_related_resource_on_fk_field(self):
        gen = FormSchemaGenerator()
        schema = gen.from_pydantic(User)
        field = schema.get_field("owner_id")
        assert field.resource == "owners"

    def test_json_schema_extra_visible_in_form_false(self):
        from pydantic import BaseModel as PydanticModel
        from pydantic import Field as PydanticField

        class Secretive(PydanticModel):
            username: str
            internal_note: str = PydanticField(
                default="",
                json_schema_extra={"visible_in_form": False},
            )

        gen = FormSchemaGenerator()
        schema = gen.from_pydantic(Secretive)
        note = schema.get_field("internal_note")
        assert note is not None
        assert note.visible_in_form is False
        assert schema.get_field("username").visible_in_form is True


class TestFormValidationEngine:
    @pytest.mark.asyncio
    async def test_field_validation(self):
        engine = FormValidationEngine()
        engine.add_field_validator("email", email)

        errors = await engine.validate_field("email", "invalid-email", {})
        assert len(errors) == 1
        assert "valid email" in errors[0].message

        valid_errors = await engine.validate_field("email", "test@example.com", {})
        assert len(valid_errors) == 0

    @pytest.mark.asyncio
    async def test_form_validation(self):
        engine = FormValidationEngine()
        engine.add_field_validator("name", required)

        data = {"name": "", "email": "wrong"}
        errors = await engine.validate_form(data)

        assert "name" in errors
        assert errors["name"][0].message == "This field is required."

    @pytest.mark.asyncio
    async def test_cross_field_validation(self):
        engine = FormValidationEngine()

        def password_match(value, data):
            if data.get("password") != data.get("confirm_password"):
                return {"confirm_password": ["Passwords do not match"]}
            return None

        engine.add_form_validator(password_match)

        data = {"password": "123", "confirm_password": "456"}
        errors = await engine.validate_form(data)

        assert "confirm_password" in errors
        assert errors["confirm_password"][0].message == "Passwords do not match"


class TestFormLayoutBuilder:
    def test_layout_build(self):
        layout = (
            FormLayoutBuilder.create()
            .section("Identity", ["username", "email"])
            .tabs({"Profile": ["bio", "age"], "Settings": ["is_active"]})
            .build()
        )

        assert len(layout) == 2
        assert layout[0].title == "Identity"
        assert len(layout[1].tabs) == 2

    def test_form_base_renders_declared_layout(self):
        from lexigram.admin.forms import FormBase, FormLayoutBuilder
        from lexigram.admin.schema import TextField

        class _ProfileForm(FormBase):
            username = TextField(name="username", label="Username", required=True)
            email = TextField(name="email", label="Email", required=False)
            layout = FormLayoutBuilder.create().section(
                "Identity", ["username", "email"]
            ).build()

        html = str(_ProfileForm(data={"username": "ada"}).render())
        assert "Identity" in html
        assert 'name="username"' in html
        assert 'value="ada"' in html

    def test_form_base_layout_constructor_override(self):
        from lexigram.admin.forms import FormBase, FormLayoutBuilder
        from lexigram.admin.schema import TextField

        class _ProfileForm(FormBase):
            name = TextField(name="name", label="Name", required=True)

        layout = FormLayoutBuilder.create().section("General", ["name"]).build()
        html = str(_ProfileForm(layout=layout).render())
        assert "General" in html
        assert 'name="name"' in html

    def test_form_base_layout_hides_visible_in_form_false_fields(self):
        from lexigram.admin.forms import FormBase, FormLayoutBuilder
        from lexigram.admin.schema import TextField

        class _ProfileForm(FormBase):
            username = TextField(name="username", label="Username", required=True)
            internal_note = TextField(
                name="internal_note",
                label="Internal note",
                required=False,
                visible_in_form=False,
            )

        layout = FormLayoutBuilder.create().section(
            "Identity",
            ["username", "internal_note"],
        ).build()
        html = str(_ProfileForm(layout=layout).render())
        assert 'name="username"' in html
        assert 'name="internal_note"' not in html

    def test_form_base_renders_formlayout_schema(self):
        from lexigram.admin.forms import FormBase, FormLayout
        from lexigram.admin.schema import TextField

        class _ProfileForm(FormBase):
            name = TextField(name="name", label="Name", required=True)
            email = TextField(name="email", label="Email", required=False)

        html = str(_ProfileForm(
            layout=FormLayout(sections=[{"title": "General", "fields": ["name"]}]),
        ).render())
        assert "General" in html
        assert 'name="name"' in html
        assert 'name="email"' not in html

    def test_form_base_renders_validation_errors(self):
        from lexigram.admin.forms import FormBase
        from lexigram.admin.schema import TextField

        class _ProfileForm(FormBase):
            email = TextField(name="email", label="Email", required=True)

        form = _ProfileForm(data={"email": ""})
        form.is_valid()
        html = str(form.render())
        assert "This field is required." in html


class TestFormStore:
    def test_store_state(self):
        store = FormStore(initial_values={"name": "Alice"})
        assert store.get_value("name") == "Alice"
        assert store.is_dirty is False

        store.set_value("name", "Bob")
        assert store.get_value("name") == "Bob"
        assert store.is_dirty is True

    @pytest.mark.asyncio
    async def test_store_validation(self):
        engine = FormValidationEngine()
        engine.add_field_validator("name", required)

        store = FormStore(initial_values={"name": ""}, validation_engine=engine)

        is_valid = await store.validate()
        assert is_valid is False
        assert "name" in store.errors


class TestBaseFormValidate:
    @pytest.mark.asyncio
    async def test_valid_data_returns_ok_with_cleaned_data(self):
        from lexigram.admin.forms import FormBase
        from lexigram.admin.schema import TextField

        class _SimpleForm(FormBase):
            name = TextField(name="name", label="Name", required=True)

        form = _SimpleForm(data={"name": "Alice"})
        result = await form.validate()

        assert result.is_ok()
        cleaned = result.unwrap()
        assert cleaned["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_invalid_data_returns_err_with_admin_validation_error(self):
        from lexigram.admin.exceptions import AdminValidationError
        from lexigram.admin.forms import FormBase
        from lexigram.admin.schema import TextField
        from lexigram.contracts.exceptions import FieldError

        class _SimpleForm(FormBase):
            name = TextField(name="name", label="Name", required=True)

        form = _SimpleForm(data={"name": ""})  # required field empty
        result = await form.validate()

        assert result.is_err()
        error = result.unwrap_err()
        assert isinstance(error, AdminValidationError)
        assert len(error.errors) == 1
        field_error = error.errors[0]
        assert isinstance(field_error, FieldError)
        assert field_error.field == "name"
        assert field_error.code == "invalid"

    @pytest.mark.asyncio
    async def test_result_match_on_valid_form(self):
        from lexigram.admin.forms import FormBase
        from lexigram.admin.schema import TextField

        class _SimpleForm(FormBase):
            title = TextField(name="title", label="Title", required=False)

        form = _SimpleForm(data={"title": "Draft"})
        result = await form.validate()

        message = result.match(
            ok=lambda d: f"saved: {d['title']}",
            err=lambda e: f"error: {e}",
        )
        assert message == "saved: Draft"

    def test_form_renders_schema_fields(self):
        from lexigram.admin.forms import FormBase
        from lexigram.admin.schema import TextField

        class _SimpleForm(FormBase):
            name = TextField(name="name", label="Name", required=True)

        html = str(_SimpleForm(data={"name": "Ada"}).render())
        assert 'name="name"' in html
        assert 'value="Ada"' in html

    def test_initial_values_are_used(self):
        from lexigram.admin.forms import FormBase
        from lexigram.admin.schema import TextField

        class _SimpleForm(FormBase):
            name = TextField(name="name", label="Name", required=True)

        form = _SimpleForm(initial={"name": "Grace"})
        assert form.values["name"] == "Grace"

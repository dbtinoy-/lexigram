"""Unit tests for the new Form System."""

from dataclasses import dataclass, field
from typing import Union

import pytest

from lexigram.admin.forms import (
    FieldType,
    FormLayoutBuilder,
    FormSchemaGenerator,
    FormStore,
    FormValidationEngine,
    email,
    required,
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
    target: Union[Role, Permission] | None = None


class TestFormSchemaGenerator:
    def test_from_pydantic_simple(self):
        gen = FormSchemaGenerator()
        schema = gen.from_pydantic(User)

        assert schema.title == "User"
        assert len(schema.fields) == 7

        username_field = schema.get_field("username")
        assert username_field.label == "Username"
        assert username_field.type == FieldType.TEXT
        assert username_field.required is True
        assert username_field.help_text == "Unique name"

        email_field = schema.get_field("email")
        assert email_field.type == FieldType.TEXT

        active_field = schema.get_field("is_active")
        assert active_field.type == FieldType.CHECKBOX
        assert active_field.default is True

    def test_from_pydantic_nested(self):
        gen = FormSchemaGenerator()
        schema = gen.from_pydantic(User)

        profile_field = schema.get_field("profile")
        assert profile_field.type == FieldType.NESTED
        assert profile_field.nested_schema is not None
        assert profile_field.nested_schema.get_field("bio") is not None

        tags_field = schema.get_field("tags")
        assert tags_field.type == FieldType.LIST

    def test_detects_belongs_to_fk(self):
        gen = FormSchemaGenerator()
        schema = gen.from_pydantic(User)

        owner_field = schema.get_field("owner_id")
        assert owner_field is not None
        assert owner_field.type == FieldType.BELONGS_TO
        assert owner_field.related_resource == "owners"

    def test_detects_has_many(self):
        gen = FormSchemaGenerator()
        schema = gen.from_pydantic(User)

        pets_field = schema.get_field("pets")
        assert pets_field is not None
        assert pets_field.type == FieldType.HAS_MANY
        assert pets_field.related_resource is None  # Not populated yet

    def test_detects_morph(self):
        gen = FormSchemaGenerator()
        schema = gen.from_pydantic(PolymorphicModel)

        target_field = schema.get_field("target")
        assert target_field is not None
        assert target_field.type == FieldType.MORPH

    def test_plain_str_id_not_detected_as_fk(self):
        @dataclass
        class Plain(DomainModel):
            identifier: str

        gen = FormSchemaGenerator()
        schema = gen.from_pydantic(Plain)
        field = schema.get_field("identifier")
        assert field.type == FieldType.TEXT

    def test_resource_registry_accepted(self):
        gen = FormSchemaGenerator(resource_registry={"users": User})
        assert gen.resource_registry == {"users": User}

    def test_related_resource_on_fk_field(self):
        gen = FormSchemaGenerator()
        schema = gen.from_pydantic(User)
        field = schema.get_field("owner_id")
        assert field.related_resource == "owners"


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
        from lexigram.admin.forms.fields import TextField

        class _SimpleForm(FormBase):
            name = TextField(label="Name", required=True)

        form = _SimpleForm(data={"name": "Alice"})
        result = await form.validate()

        assert result.is_ok()
        cleaned = result.unwrap()
        assert cleaned["name"] == "Alice"

    @pytest.mark.asyncio
    async def test_invalid_data_returns_err_with_admin_validation_error(self):
        from lexigram.admin.exceptions import AdminValidationError
        from lexigram.admin.forms import FormBase
        from lexigram.admin.forms.fields import TextField
        from lexigram.contracts.exceptions import FieldError

        class _SimpleForm(FormBase):
            name = TextField(label="Name", required=True)

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
        from lexigram.admin.forms.fields import TextField

        class _SimpleForm(FormBase):
            title = TextField(label="Title", required=False)

        form = _SimpleForm(data={"title": "Draft"})
        result = await form.validate()

        message = result.match(
            ok=lambda d: f"saved: {d['title']}",
            err=lambda e: f"error: {e}",
        )
        assert message == "saved: Draft"

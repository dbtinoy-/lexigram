"""Unit tests for the shared form guard (mass-assignment protection)."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import ClassVar

from lexigram.admin.resources.form_guard import (
    PROTECTED_FORM_FIELDS,
    model_field_names,
    sanitize_form_data,
)


@dataclass
class GuardModel:
    name: str = ""
    is_active: bool = True
    _private: str = ""  # noqa: S105 — fixture only
    extra: ClassVar[str] = "class-level"


def test_protected_fields_are_framework_managed() -> None:
    assert PROTECTED_FORM_FIELDS == frozenset(
        {"id", "tenant_id", "created_at", "updated_at"}
    )


def test_model_field_names_excludes_private_and_classvar() -> None:
    assert model_field_names(GuardModel) == {"name", "is_active"}


def test_model_field_names_none_returns_empty() -> None:
    assert model_field_names(None) == set()


def test_sanitize_strips_protected_keys_with_model() -> None:
    cleaned = sanitize_form_data(
        {
            "name": "Rex",
            "id": "999",
            "tenant_id": "evil",
            "created_at": "2020-01-01",
            "updated_at": "2020-01-02",
            "is_active": "on",
        },
        model=GuardModel,
    )
    assert cleaned == {"name": "Rex", "is_active": True}


def test_sanitize_drops_unknown_keys_by_default() -> None:
    cleaned = sanitize_form_data(
        {"name": "Rex", "role": "superadmin"},
        model=GuardModel,
    )
    assert cleaned == {"name": "Rex"}


def test_sanitize_allow_extra_fields_keeps_unknown_but_strips_protected() -> None:
    cleaned = sanitize_form_data(
        {"name": "Rex", "role": "editor", "id": "999"},
        model=GuardModel,
        allow_extra_fields=True,
    )
    assert cleaned == {"name": "Rex", "role": "editor"}


def test_sanitize_untyped_model_keeps_unknown_but_strips_protected() -> None:
    cleaned = sanitize_form_data(
        {"anything": 1, "tenant_id": "evil", "id": "999"},
        model=None,
    )
    assert cleaned == {"anything": 1}


def test_sanitize_never_mutates_input() -> None:
    raw = {"name": "Rex", "id": "999"}
    sanitize_form_data(raw, model=GuardModel)
    assert raw == {"name": "Rex", "id": "999"}


def test_sanitize_dataclass_field_defaults_are_not_writable() -> None:
    """ClassVar members (e.g. ``extra``) must never be accepted as fields."""

    @dataclass
    class WithClassVar:
        name: str = field(default="")
        marker: ClassVar[str] = "x"

    cleaned = sanitize_form_data({"name": "A", "marker": "forged"}, model=WithClassVar)
    assert cleaned == {"name": "A"}

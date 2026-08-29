"""Live handler path must apply the same mass-assignment guard as controllers."""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.admin.resources.base import Resource
from lexigram.result import Ok


@dataclass
class _Account:
    name: str = ""
    is_active: bool = True


class _AccountResource(Resource):
    model = _Account
    name = "accounts"


async def test_before_validate_strips_protected_and_unknown_keys() -> None:
    resource = _AccountResource()
    result = await resource.before_validate(
        {
            "name": "Ada",
            "id": "999",
            "tenant_id": "evil",
            "created_at": "2020-01-01",
            "role": "superadmin",
            "is_active": "on",
        }
    )

    assert isinstance(result, Ok)
    assert result.unwrap() == {"name": "Ada", "is_active": True}


async def test_before_validate_respects_custom_protected_fields() -> None:
    class _TightResource(Resource):
        model = _Account
        name = "tight"
        protected_form_fields = frozenset({"id", "tenant_id", "created_at", "updated_at", "owner_id"})

    resource = _TightResource()
    result = await resource.before_validate({"name": "Ada", "owner_id": "9"})

    assert isinstance(result, Ok)
    assert result.unwrap() == {"name": "Ada"}


async def test_before_validate_allow_extra_fields_keeps_unknowns() -> None:
    class _LooseResource(Resource):
        model = _Account
        name = "loose"
        form_allow_extra_fields = True

    resource = _LooseResource()
    result = await resource.before_validate(
        {"name": "Ada", "custom_note": "keep", "id": "999"}
    )

    assert isinstance(result, Ok)
    assert result.unwrap() == {"name": "Ada", "custom_note": "keep"}

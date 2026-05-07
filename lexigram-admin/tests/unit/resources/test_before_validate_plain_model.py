"""Tests that before_validate tolerates non-pydantic (dataclass) models."""

from __future__ import annotations

from dataclasses import dataclass

from lexigram.admin.resources.base import Resource
from lexigram.result import Ok


@dataclass
class _PlainRecord:
    """A plain dataclass model with no pydantic methods."""

    name: str = ""
    is_active: bool = True


class _PlainResource(Resource):
    """Resource bound to a plain dataclass model."""

    model = _PlainRecord
    name = "plain_records"


async def test_before_validate_passes_dataclass_model_through() -> None:
    resource = _PlainResource()
    data = {"name": "Ada", "is_active": "on"}

    result = await resource.before_validate(data)

    assert isinstance(result, Ok)
    assert result.unwrap()["name"] == "Ada"
    assert result.unwrap()["is_active"] is True


async def test_before_validate_no_model() -> None:
    class _NoModelResource(Resource):
        """Resource without a model."""

    resource = _NoModelResource()

    result = await resource.before_validate({"email": "a@b.co"})

    assert isinstance(result, Ok)
    assert result.unwrap()["email"] == "a@b.co"

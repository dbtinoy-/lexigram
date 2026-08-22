"""Mass-assignment guard: unknown/protected keys never reach the data source."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

import pytest

from lexigram.admin.controllers.resource import (
    ResourceController,
    ResourceMeta,
)


@dataclass
class Pet:
    name: str = ""
    is_active: bool = True


class _DS:
    def __init__(self):
        self.created: list[dict[str, Any]] = []

    async def create(self, data):
        self.created.append(dict(data))
        return {"id": "1", **data}

    async def update(self, item_id, data):
        self.created.append(dict(data))
        return {"id": item_id, **data}


def _controller(ds: _DS) -> ResourceController[Pet]:
    class _Concrete(ResourceController[Pet]):
        pass

    return _Concrete(
        data_source=ds,
        meta=ResourceMeta(
            name="pets", prefix="/admin/pets", label="Pets", label_plural="Pets"
        ),
    )


@pytest.mark.asyncio
async def test_unknown_and_protected_keys_stripped_on_create():
    ds = _DS()
    ctrl = _controller(ds)
    validated = ctrl.validate_create(
        {
            "name": "Rex",
            "role": "superadmin",
            "tenant_id": "other",
            "id": "999",
            "is_active": "on",
        }
    )
    await ds.create(validated)
    assert set(ds.created[0]) <= {"name", "is_active"}


@pytest.mark.asyncio
async def test_form_bool_string_coerced_on_create():
    ds = _DS()
    ctrl = _controller(ds)
    validated = ctrl.validate_create({"name": "Rex", "is_active": "on"})
    await ds.create(validated)
    assert ds.created[0]["is_active"] is True


@pytest.mark.asyncio
async def test_update_strips_protected_and_unknown_keys():
    ds = _DS()
    ctrl = _controller(ds)
    validated = ctrl.validate_update(
        "7", {"name": "Rex", "tenant_id": "evil", "role": "root"}
    )
    await ds.update("7", validated)
    assert set(ds.created[0]) == {"name"}


@pytest.mark.asyncio
async def test_untyped_controller_keeps_raw_passthrough() -> None:
    """Controllers without a bound model keep today's passthrough behavior."""

    class Untyped(ResourceController):
        pass

    ds = _DS()
    ctrl = Untyped(
        data_source=ds,
        meta=ResourceMeta(name="x", prefix="/admin/x", label="X", label_plural="X"),
    )
    validated = ctrl.validate_create({"anything": 1})
    assert validated == {"anything": 1}

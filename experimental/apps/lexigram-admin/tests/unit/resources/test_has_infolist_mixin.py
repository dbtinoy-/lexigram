from __future__ import annotations

from datetime import date

from pydantic import BaseModel

from lexigram.admin.resources import HasInfolist
from lexigram.admin.schema import BooleanField, EmailField, TextField
from lexigram.ui import InfolistEntryType


class _Model(BaseModel):
    name: str
    active: bool
    since: date


class _InfolistResource(HasInfolist):
    model = _Model


class _FieldResource(HasInfolist):
    fields = [
        EmailField(name="email"),
        TextField(name="name"),
        BooleanField(name="active"),
    ]


class _HiddenFieldResource(HasInfolist):
    fields = [TextField(name="secret", visible_in_view=False)]


class TestHasInfolist:
    def test_derives_entries_from_model(self) -> None:
        resource = _InfolistResource()
        records = {"name": "Acme", "active": True, "since": date(2026, 5, 28)}

        entries = resource.infolist(records)

        assert {e.name for e in entries} == {"name", "active", "since"}
        by_name = {e.name: e for e in entries}
        assert by_name["active"].type == InfolistEntryType.BOOLEAN
        assert by_name["since"].type == InfolistEntryType.DATE

    def test_uses_declarative_fields(self) -> None:
        resource = _FieldResource()
        records = {"email": "a@b.c", "name": "Acme", "active": True}

        entries = resource.infolist(records)

        by_name = {e.name: e for e in entries}
        assert by_name["email"].type == InfolistEntryType.EMAIL
        assert by_name["active"].type == InfolistEntryType.BOOLEAN

    def test_respects_visible_in_view(self) -> None:
        resource = _HiddenFieldResource()

        entries = resource.infolist({"secret": "classified"})

        assert entries == []

    def test_skips_missing_record_keys(self) -> None:
        resource = _InfolistResource()
        entries = resource.infolist({"name": "Acme"})

        assert {e.name for e in entries} == {"name"}

    def test_no_model_no_fields_returns_empty(self) -> None:
        resource = HasInfolist()

        assert resource.infolist({"x": 1}) == []

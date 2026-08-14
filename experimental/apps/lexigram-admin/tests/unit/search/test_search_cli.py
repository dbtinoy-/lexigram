from __future__ import annotations

from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.admin.cli.commands.search import (
    _build_documents,
    _collect_searchable,
    create_app,
)
from lexigram.admin.cli.contributor import AdminCliContributor

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _spec(index_name: str = "items", fields: tuple[str, ...] = ("name",)) -> Any:
    s = type("Spec", (), {"index_name": index_name, "fields": fields})
    return s()


class _FakeContributor:
    def __init__(self, resources: list[type]) -> None:
        self._resources = resources
        self.name = "test"
        self.contributor_id = "test"
        self.package_source = "test_pkg"

    def get_resources(self) -> list[type]:
        return self._resources


# ---------------------------------------------------------------------------
# _build_documents
# ---------------------------------------------------------------------------


class _FakeSpec:
    def __init__(self, fields: tuple[str, ...]) -> None:
        self.fields = fields


class _Record:
    def __init__(self, **kwargs: Any) -> None:
        for k, v in kwargs.items():
            setattr(self, k, v)


class TestBuildDocuments:
    def test_empty_records(self) -> None:
        spec = _FakeSpec(fields=("name", "email"))
        assert _build_documents([], spec) == []

    def test_object_records_with_id_and_fields(self) -> None:
        spec = _FakeSpec(fields=("name",))
        records = [_Record(id="1", name="Alice")]
        docs = _build_documents(records, spec)
        assert docs == [{"id": "1", "name": "Alice"}]

    def test_dict_records(self) -> None:
        spec = _FakeSpec(fields=("name", "email"))
        records = [{"id": "2", "name": "Bob", "email": "bob@test.com"}]
        docs = _build_documents(records, spec)
        assert docs == [{"id": "2", "name": "Bob", "email": "bob@test.com"}]

    def test_skips_records_without_id(self) -> None:
        spec = _FakeSpec(fields=("name",))
        records = [
            _Record(id="1", name="Alice"),
            _Record(id=None, name="NoId"),
            {"not_id": "x", "name": "DictNoId"},
        ]
        docs = _build_documents(records, spec)
        assert len(docs) == 1
        assert docs[0]["id"] == "1"

    def test_missing_field_defaults_to_none(self) -> None:
        spec = _FakeSpec(fields=("name", "missing_field"))
        records = [_Record(id="1", name="Alice")]
        docs = _build_documents(records, spec)
        assert docs == [{"id": "1", "name": "Alice", "missing_field": None}]

    def test_dict_missing_field_defaults_to_none(self) -> None:
        spec = _FakeSpec(fields=("name", "missing_field"))
        records = [{"id": "1", "name": "Alice"}]
        docs = _build_documents(records, spec)
        assert docs == [{"id": "1", "name": "Alice", "missing_field": None}]

    def test_id_is_str_converted(self) -> None:
        spec = _FakeSpec(fields=("name",))
        records = [_Record(id=42, name="Answer")]
        docs = _build_documents(records, spec)
        assert docs == [{"id": "42", "name": "Answer"}]

    def test_multiple_records(self) -> None:
        spec = _FakeSpec(fields=("title",))
        records = [
            _Record(id="a", title="First"),
            _Record(id="b", title="Second"),
        ]
        docs = _build_documents(records, spec)
        assert len(docs) == 2
        assert docs[0] == {"id": "a", "title": "First"}
        assert docs[1] == {"id": "b", "title": "Second"}


# ---------------------------------------------------------------------------
# _collect_searchable
# ---------------------------------------------------------------------------


class TestCollectSearchable:
    async def test_returns_empty_when_no_registry(self) -> None:
        container = MagicMock()
        container.resolve = AsyncMock(side_effect=Exception("no registry"))
        result = await _collect_searchable(container)
        assert result == []

    async def test_returns_searchable_resources(self) -> None:
        class SearchableRes:
            searchable = _spec()

        class NonSearchableRes:
            pass

        class NoIndexRes:
            searchable = _spec(fields=(), index_name=None)

        contributor = _FakeContributor(
            resources=[SearchableRes, NonSearchableRes, NoIndexRes]
        )

        registry = MagicMock()
        registry.get_all.return_value = [contributor]

        container = MagicMock()
        container.resolve = AsyncMock(return_value=registry)

        result = await _collect_searchable(container)
        assert len(result) == 1
        assert result[0][1].index_name == "items"


# ---------------------------------------------------------------------------
# create_app
# ---------------------------------------------------------------------------


class TestCreateApp:
    def test_returns_typer_app(self) -> None:
        app = create_app()
        assert app is not None
        assert app.info.name == "search" or "search" in str(app.info.name)

    def test_app_has_reindex_command(self) -> None:
        app = create_app()
        assert len(app.registered_commands) == 1
        cmd = app.registered_commands[0]
        assert cmd.callback is not None
        assert cmd.callback.__name__ == "reindex"


# ---------------------------------------------------------------------------
# AdminCliContributor.get_commands
# ---------------------------------------------------------------------------


class TestAdminCliContributorCommands:
    def test_returns_search_contribution(self) -> None:
        contributor = AdminCliContributor()
        commands = contributor.get_commands()
        assert len(commands) == 1
        cmd = commands[0]
        assert cmd.name == "search"
        assert cmd.contributor == "admin"
        assert (
            cmd.app_factory_path
            == "lexigram.admin.cli.commands.search:create_app"
        )

"""Tests for GraphQL query whitelist."""

import pytest
from lexigram.graphql.security.query_whitelist import (
    QueryWhitelist,
    WhitelistEntry,
    default_whitelist,
)


class TestWhitelistEntry:
    def test_whitelist_entry_creation(self) -> None:
        entry = WhitelistEntry(
            hash="abc123",
            query="{ user { id } }",
            operation_name="GetUser",
            description="Get user by ID",
        )
        assert entry.hash == "abc123"
        assert entry.query == "{ user { id } }"
        assert entry.operation_name == "GetUser"
        assert entry.description == "Get user by ID"


class TestQueryWhitelist:
    def test_whitelist_creation_disabled(self) -> None:
        whitelist = QueryWhitelist()
        assert whitelist.enabled is False

    def test_whitelist_creation_enabled(self) -> None:
        whitelist = QueryWhitelist(enabled=True)
        assert whitelist.enabled is True

    def test_add_query(self) -> None:
        whitelist = QueryWhitelist()
        entry = whitelist.add("{ user { id } }", "Get user")
        assert entry is not None
        assert entry.query == "{ user { id } }"

    def test_is_allowed_when_disabled(self) -> None:
        whitelist = QueryWhitelist(enabled=False)
        assert whitelist.is_allowed("{ any { query } }") is True

    def test_is_allowed_when_enabled_no_match(self) -> None:
        whitelist = QueryWhitelist(enabled=True)
        assert whitelist.is_allowed("{ user { id } }") is False

    def test_is_allowed_when_enabled_with_match(self) -> None:
        whitelist = QueryWhitelist(enabled=True)
        whitelist.add("{ user { id } }")
        assert whitelist.is_allowed("{ user { id } }") is True

    def test_is_allowed_normalizes_whitespace(self) -> None:
        whitelist = QueryWhitelist(enabled=True)
        whitelist.add("{ user { id } }")
        assert whitelist.is_allowed("{    user    {    id    }    }") is True

    def test_remove_query(self) -> None:
        whitelist = QueryWhitelist(enabled=True)
        whitelist.add("{ user { id } }")
        result = whitelist.remove("{ user { id } }")
        assert result is True
        assert whitelist.is_allowed("{ user { id } }") is False

    def test_remove_nonexistent_query(self) -> None:
        whitelist = QueryWhitelist()
        result = whitelist.remove("{ user { id } }")
        assert result is False

    def test_get_entry(self) -> None:
        whitelist = QueryWhitelist()
        whitelist.add("{ user { id } }", "Get user")
        entry = whitelist.get_entry("{ user { id } }")
        assert entry is not None
        assert entry.description == "Get user"

    def test_get_entry_nonexistent(self) -> None:
        whitelist = QueryWhitelist()
        entry = whitelist.get_entry("{ user { id } }")
        assert entry is None

    def test_get_all_hashes(self) -> None:
        whitelist = QueryWhitelist()
        whitelist.add("{ user { id } }")
        whitelist.add("{ post { id } }")
        hashes = whitelist.get_all_hashes()
        assert len(hashes) == 2

    def test_clear(self) -> None:
        whitelist = QueryWhitelist()
        whitelist.add("{ user { id } }")
        whitelist.clear()
        assert len(whitelist.get_all_hashes()) == 0

    def test_default_whitelist_exists(self) -> None:
        assert default_whitelist is not None
        assert isinstance(default_whitelist, QueryWhitelist)

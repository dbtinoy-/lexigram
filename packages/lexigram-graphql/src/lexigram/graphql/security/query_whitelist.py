"""Query whitelist for production GraphQL endpoints.

This module provides query whitelisting to restrict GraphQL
operations to a predefined set for security.
"""

from __future__ import annotations

from dataclasses import dataclass

from lexigram import hashing  # type: ignore[attr-defined]


@dataclass
class WhitelistEntry:
    """A whitelisted query entry.

    Attributes:
        hash: SHA256 hash of the query.
        query: The actual query string.
        operation_name: Optional operation name.
        description: Human-readable description.
    """

    hash: str
    query: str
    operation_name: str | None = None
    description: str | None = None


class QueryWhitelist:
    """Query whitelist manager.

    Example:
        whitelist = QueryWhitelist()
        whitelist.add("{ user { id name } }", "Get user")

        # Validate incoming queries
        if not whitelist.is_allowed(query):
            raise PermissionError("Query not whitelisted")
    """

    def __init__(self, enabled: bool = False):
        """Initialize the whitelist.

        Args:
            enabled: Whether whitelist enforcement is enabled.
        """
        self._enabled = enabled
        self._entries: dict[str, WhitelistEntry] = {}

    @property
    def enabled(self) -> bool:
        """Check if whitelist is enabled."""
        return self._enabled

    def add(
        self,
        query: str,
        description: str | None = None,
        operation_name: str | None = None,
    ) -> WhitelistEntry:
        """Add a query to the whitelist.

        Args:
            query: GraphQL query string.
            description: Optional description.
            operation_name: Optional operation name.

        Returns:
            The created whitelist entry.
        """
        hash_value = self._compute_hash(query)

        entry = WhitelistEntry(
            hash=hash_value,
            query=query,
            operation_name=operation_name,
            description=description,
        )

        self._entries[hash_value] = entry
        return entry

    def remove(self, query: str) -> bool:
        """Remove a query from the whitelist.

        Args:
            query: GraphQL query string.

        Returns:
            True if removed, False if not found.
        """
        hash_value = self._compute_hash(query)

        if hash_value in self._entries:
            del self._entries[hash_value]
            return True

        return False

    def is_allowed(self, query: str) -> bool:
        """Check if a query is allowed.

        Args:
            query: GraphQL query string.

        Returns:
            True if allowed, False otherwise.
        """
        if not self._enabled:
            return True

        hash_value = self._compute_hash(query)
        return hash_value in self._entries

    def get_entry(self, query: str) -> WhitelistEntry | None:
        """Get the whitelist entry for a query.

        Args:
            query: GraphQL query string.

        Returns:
            Whitelist entry if found, None otherwise.
        """
        hash_value = self._compute_hash(query)
        return self._entries.get(hash_value)

    def get_all_hashes(self) -> set[str]:
        """Get all whitelisted query hashes.

        Returns:
            Set of query hashes.
        """
        return set(self._entries.keys())

    def clear(self) -> None:
        """Clear all whitelist entries."""
        self._entries.clear()

    def _compute_hash(self, query: str) -> str:
        """Compute SHA256 hash of a query.

        Args:
            query: GraphQL query string.

        Returns:
            Hex-encoded hash.
        """
        # Normalize query (remove extra whitespace)
        normalized = " ".join(query.split())
        return str(hashing.hash_hex(normalized))


# Default whitelist instance
default_whitelist = QueryWhitelist()


__all__ = [
    "QueryWhitelist",
    "WhitelistEntry",
    "default_whitelist",
]

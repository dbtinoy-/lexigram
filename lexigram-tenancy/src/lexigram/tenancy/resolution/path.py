"""Path-based tenant resolver."""

from __future__ import annotations

import re

from lexigram.contracts.tenancy.types import TenantResolutionContext


class PathTenantResolver:
    """Resolves tenant from a path segment.

    Given ``path_pattern="/tenants/{tenant_id}/"`` and a request to
    ``/tenants/acme/users``, returns ``"acme"``.

    Priority 40 — lowest default trust level.

    Attributes:
        name: ``"path"``
        priority: ``40``
    """

    name: str = "path"
    priority: int = 40

    def __init__(self, path_pattern: str = "/tenants/{tenant_id}/") -> None:
        """Initialise the resolver.

        Args:
            path_pattern: Path template where ``{tenant_id}`` is the
                placeholder to extract.  The pattern is converted to a
                regex automatically.
        """
        self._pattern = self._compile(path_pattern)

    @staticmethod
    def _compile(pattern: str) -> re.Pattern[str]:
        """Convert a ``{tenant_id}`` pattern to a compiled regex.

        Args:
            pattern: Path pattern string.

        Returns:
            Compiled regular expression with a ``tenant_id`` named group.
        """
        # Escape everything except the placeholder, then replace it with a
        # named capture group.
        escaped = re.escape(pattern)
        regex = escaped.replace(r"\{tenant_id\}", r"(?P<tenant_id>[^/]+)")
        return re.compile(regex)

    async def resolve(self, context: TenantResolutionContext) -> str | None:
        """Extract the tenant ID from the request path.

        Args:
            context: Immutable request resolution context.

        Returns:
            The captured ``tenant_id`` segment, or ``None`` if the path does
            not match the configured pattern.
        """
        path = context.path
        if not path:
            return None
        match = self._pattern.search(path)
        if match:
            return match.group("tenant_id") or None
        return None


__all__ = ["PathTenantResolver"]

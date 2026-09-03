"""Per-user saved list views (roadmap R13).

Persists named list-view states (search, filters, sort, pagination size,
view/layout/density, grouping, hidden columns) per admin user and per
resource, on top of :class:`AdminSettingsService` — no schema migration.
Design: docs/09-01-2026/08-saved-views.md.

Storage shape (JSON via tenant_configs)::

    key   = admin.saved_views.{user_id}.{resource}
    value = [{"name": str, "query": str, "created_at": iso8601}, ...]
"""

from __future__ import annotations

from datetime import UTC, datetime
import re
from typing import Any
from urllib.parse import parse_qsl, urlencode

from lexigram.logging import get_logger

logger = get_logger(__name__)

__all__ = ["SavedViewError", "SavedViewService"]

#: Canonical TableState query params that are safe to persist and replay.
ALLOWED_PARAMS: frozenset[str] = frozenset(
    {
        "search",
        "per_page",
        "sort_by",
        "sort_order",
        "data_view",
        "layout_type",
        "density",
        "group_by",
        "hide_cols",
        "col_order",
        "collapsed_groups",
        "include_deleted",
    }
)

#: Legacy aliases accepted in URLs, canonicalized on save.
LEGACY_ALIASES: dict[str, str] = {
    "q": "search",
    "sort": "sort_by",
    "order": "sort_order",
    "dir": "sort_order",
}

FILTER_PREFIX = "filter_"

MAX_VIEWS_PER_RESOURCE = 20
MAX_NAME_LENGTH = 64
MAX_QUERY_LENGTH = 2000

_RESOURCE_RE = re.compile(r"^[a-z0-9_-]{1,64}$")
_CONTROL_CHARS_RE = re.compile(r"[\x00-\x1f\x7f]")

_KEY_NAMESPACE = "saved_views"


class SavedViewError(ValueError):
    """User-facing validation error for saved-view operations."""


class SavedViewService:
    """CRUD for per-user, per-resource saved list views.

    Args:
        settings_service: An :class:`AdminSettingsService` (or compatible
            object with async ``get``/``set``). ``None`` degrades to a
            no-op read path so callers never crash.
        tenant_id: Storage scope; saved views are user preferences, so a
            single shared scope is used by default.
    """

    def __init__(self, settings_service: Any, tenant_id: str = "default") -> None:
        self._settings = settings_service
        self._tenant_id = tenant_id

    # -- validation / normalization -----------------------------------------

    @staticmethod
    def sanitize_query(query: str) -> str:
        """Return a canonical, whitelisted query string (no leading ``?``).

        Keeps only known TableState params (plus ``filter_*``), maps legacy
        aliases to canonical names and drops volatile params such as
        ``page``, ``cursor`` and flash-message params.

        Args:
            query: Raw query string, with or without a leading ``?``.

        Returns:
            Re-encoded canonical query string (possibly empty).
        """
        raw = (query or "").lstrip("?")
        if not raw:
            return ""
        kept: list[tuple[str, str]] = []
        seen: set[str] = set()
        for key, value in parse_qsl(raw, keep_blank_values=False):
            canonical = LEGACY_ALIASES.get(key, key)
            allowed = canonical in ALLOWED_PARAMS or (
                canonical.startswith(FILTER_PREFIX)
                and len(canonical) > len(FILTER_PREFIX)
            )
            if not allowed or canonical in seen or value == "":
                continue
            seen.add(canonical)
            kept.append((canonical, value))
        return urlencode(kept)

    @staticmethod
    def _validate_resource(resource: str) -> str:
        slug = (resource or "").strip()
        if not _RESOURCE_RE.match(slug):
            raise SavedViewError("Invalid resource name.")
        return slug

    @staticmethod
    def _validate_name(name: str) -> str:
        cleaned = _CONTROL_CHARS_RE.sub("", (name or "").strip())
        if not cleaned:
            raise SavedViewError("View name is required.")
        if len(cleaned) > MAX_NAME_LENGTH:
            raise SavedViewError(
                f"View name must be at most {MAX_NAME_LENGTH} characters."
            )
        return cleaned

    @staticmethod
    def _validate_user_id(user_id: str) -> str:
        cleaned = str(user_id or "").strip()
        if not cleaned or cleaned == "guest":
            raise SavedViewError("A signed-in user is required.")
        return cleaned

    def _key(self, user_id: str, resource: str) -> str:
        return f"{_KEY_NAMESPACE}.{user_id}.{resource}"

    @staticmethod
    def _coerce_views(raw: Any) -> list[dict[str, str]]:
        """Tolerate corrupt payloads: keep only well-formed view entries."""
        views: list[dict[str, str]] = []
        if not isinstance(raw, list):
            return views
        for item in raw:
            if not isinstance(item, dict):
                continue
            name = str(item.get("name") or "").strip()
            query = str(item.get("query") or "")
            if not name:
                continue
            views.append(
                {
                    "name": name[:MAX_NAME_LENGTH],
                    "query": query[:MAX_QUERY_LENGTH],
                    "created_at": str(item.get("created_at") or ""),
                }
            )
        return views

    # -- public API ----------------------------------------------------------

    async def list_views(self, user_id: str, resource: str) -> list[dict[str, str]]:
        """Return the user's saved views for a resource (sorted by name).

        Never raises: storage errors and corrupt payloads degrade to ``[]``.
        """
        if self._settings is None:
            return []
        try:
            user = self._validate_user_id(user_id)
            slug = self._validate_resource(resource)
        except SavedViewError:
            return []
        try:
            raw = await self._settings.get(self._tenant_id, self._key(user, slug))
        except Exception as exc:  # noqa: BLE001 — reads must never break the list page
            logger.warning("saved_views.read_failed", error=str(exc))
            return []
        views = self._coerce_views(raw)
        views.sort(key=lambda v: v["name"].casefold())
        return views

    async def save_view(
        self, user_id: str, resource: str, name: str, query: str
    ) -> dict[str, str]:
        """Create or update (by case-insensitive name) a saved view.

        Args:
            user_id: Owning admin user id.
            resource: Resource slug the view belongs to.
            name: User-chosen view name (1–64 chars).
            query: Raw query string to sanitize and persist.

        Returns:
            The stored view entry.

        Raises:
            SavedViewError: Invalid input, empty sanitized query, view-count
                cap reached, or storage unavailable.
        """
        if self._settings is None:
            raise SavedViewError("Saved views storage is unavailable.")
        user = self._validate_user_id(user_id)
        slug = self._validate_resource(resource)
        cleaned_name = self._validate_name(name)
        sanitized = self.sanitize_query(query)
        if not sanitized:
            raise SavedViewError(
                "Nothing to save — apply a search, filter or sort first."
            )
        if len(sanitized) > MAX_QUERY_LENGTH:
            raise SavedViewError("View query is too long to save.")

        views = self._coerce_views(
            await self._settings.get(self._tenant_id, self._key(user, slug))
        )
        entry = {
            "name": cleaned_name,
            "query": sanitized,
            "created_at": datetime.now(UTC).isoformat(),
        }
        replaced = False
        for idx, view in enumerate(views):
            if view["name"].casefold() == cleaned_name.casefold():
                entry["created_at"] = view.get("created_at") or entry["created_at"]
                views[idx] = entry
                replaced = True
                break
        if not replaced:
            if len(views) >= MAX_VIEWS_PER_RESOURCE:
                raise SavedViewError(
                    f"Limit of {MAX_VIEWS_PER_RESOURCE} saved views reached "
                    "for this resource — delete one first."
                )
            views.append(entry)
        views.sort(key=lambda v: v["name"].casefold())
        try:
            await self._settings.set(self._tenant_id, self._key(user, slug), views)
        except Exception as exc:  # noqa: BLE001 — surface a friendly message
            logger.error("saved_views.write_failed", error=str(exc))
            raise SavedViewError("Could not save the view — try again.") from exc
        logger.info(
            "saved_views.saved",
            user_id=user,
            resource=slug,
            name=cleaned_name,
            replaced=replaced,
        )
        return entry

    async def delete_view(self, user_id: str, resource: str, name: str) -> bool:
        """Delete a saved view by (case-insensitive) name.

        Returns:
            True if a view was removed, False if no such view existed.

        Raises:
            SavedViewError: Invalid input or storage unavailable/failed.
        """
        if self._settings is None:
            raise SavedViewError("Saved views storage is unavailable.")
        user = self._validate_user_id(user_id)
        slug = self._validate_resource(resource)
        cleaned_name = self._validate_name(name)

        views = self._coerce_views(
            await self._settings.get(self._tenant_id, self._key(user, slug))
        )
        remaining = [
            v for v in views if v["name"].casefold() != cleaned_name.casefold()
        ]
        if len(remaining) == len(views):
            return False
        try:
            await self._settings.set(
                self._tenant_id, self._key(user, slug), remaining
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("saved_views.delete_failed", error=str(exc))
            raise SavedViewError("Could not delete the view — try again.") from exc
        logger.info(
            "saved_views.deleted", user_id=user, resource=slug, name=cleaned_name
        )
        return True

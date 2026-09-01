"""Revision history, diff, and revert endpoints for the resource controller.

``RevisionService`` recorded a snapshot after every create and update, but
nothing ever read those snapshots back: no route listed them, compared them,
or applied one, so ``revert_data()`` was unreachable. This mixin exposes that
history and routes a revert through the controller's own update path so
validation, permissions, auditing, and snapshotting all still apply.
"""

from __future__ import annotations

import html
import inspect
from typing import Any

from starlette.requests import Request
from starlette.responses import HTMLResponse, Response

from lexigram.admin.controllers.resource.meta import ResourceMeta
from lexigram.logging import get_logger

logger = get_logger(__name__)

# Revert restores a prior snapshot of user-editable fields. Identity and
# audit columns describe when a row existed, not what it contained, so
# replaying them would rewrite history rather than restore content.
_NON_RESTORABLE_FIELDS = frozenset(
    {"id", "tenant_id", "created_at", "updated_at", "deleted_at"}
)

_MAX_VALUE_CHARS = 200


class ResourceRevisionMixin:
    """History, diff, and revert handlers backed by ``RevisionService``."""

    # Host attributes provided by sibling mixins on ResourceController.
    meta: ResourceMeta
    _revision_service: Any
    _record_permission: Any
    _record_mapping: Any
    _resource_url: Any
    _emit_audit: Any
    _record_revision: Any
    get_data_source: Any
    validate_update: Any

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_value(value: Any) -> str:
        """Return a short, HTML-safe rendering of a field value."""
        if value is None:
            text = "—"
        elif isinstance(value, bool):
            text = "true" if value else "false"
        else:
            text = str(value)
        if len(text) > _MAX_VALUE_CHARS:
            text = f"{text[:_MAX_VALUE_CHARS]}…"
        return html.escape(text)

    def _revision_url(self, request: Request, item_id: str, suffix: str = "") -> str:
        """Build a URL under this resource's revision namespace."""
        base = self._resource_url(request, f"{item_id}/revisions")
        return f"{base}{suffix}"

    async def _load_record(self, item_id: str) -> Any:
        """Fetch a record, returning ``None`` when absent or unavailable."""
        data_source = self.get_data_source()
        lookup = data_source.find_one(item_id)
        return await lookup if inspect.isawaitable(lookup) else lookup

    def _restorable(self, data: dict[str, Any]) -> dict[str, Any]:
        """Strip identity and audit columns from a snapshot before applying."""
        excluded = set(_NON_RESTORABLE_FIELDS)
        excluded.update(getattr(self, "readonly_fields", ()) or ())
        excluded.update(getattr(self, "form_exclude_fields", ()) or ())
        return {key: value for key, value in data.items() if key not in excluded}

    # ------------------------------------------------------------------
    # Handlers
    # ------------------------------------------------------------------

    async def revision_history(self, request: Request) -> Response:
        """List stored revisions for a record, newest first."""
        if self._revision_service is None:
            return HTMLResponse("Revision history is not enabled", status_code=404)

        item_id = str(request.path_params.get("id", ""))
        if not await self._record_permission(request, "can_view"):
            return HTMLResponse("Forbidden", status_code=403)

        try:
            revisions = await self._revision_service.list_revisions(
                getattr(self.meta, "name", "resource"), item_id
            )
        except Exception:  # noqa: BLE001 — history must not break the page
            logger.exception("admin.revision_history_failed")
            return HTMLResponse("Unable to load revision history", status_code=503)

        can_revert = await self._record_permission(request, "can_update")
        rows: list[str] = []
        for index, revision in enumerate(revisions):
            created = html.escape(str(getattr(revision, "created_at", "")))
            actor = html.escape(str(getattr(revision, "actor_id", "")))
            comment = html.escape(str(getattr(revision, "comment", "")))
            rev_id = html.escape(str(getattr(revision, "revision_id", "")))
            # The newest revision is the current state; reverting to it is a
            # no-op, so it is offered as a diff target only.
            action = ""
            if can_revert and index > 0:
                action = (
                    f'<form method="POST" '
                    f'action="{self._revision_url(request, item_id, f"/{rev_id}/revert")}">'
                    f'<button type="submit" name="revision_id" value="{rev_id}">'
                    f"Restore</button></form>"
                )
            rows.append(
                f'<tr data-revision-id="{rev_id}">'
                f"<td>{created}</td><td>{actor}</td><td>{comment}</td>"
                f"<td>{action}</td></tr>"
            )

        if not rows:
            body = "<p>No revisions recorded for this record yet.</p>"
        else:
            body = (
                "<table><thead><tr><th>When</th><th>Who</th>"
                "<th>Comment</th><th></th></tr></thead>"
                f"<tbody>{''.join(rows)}</tbody></table>"
            )

        label = html.escape(str(getattr(self.meta, "label", "Record")))
        return HTMLResponse(f"<h2>{label} history</h2>{body}")

    async def revision_diff(self, request: Request) -> Response:
        """Compare two revisions of a record field by field."""
        if self._revision_service is None:
            return HTMLResponse("Revision history is not enabled", status_code=404)

        if not await self._record_permission(request, "can_view"):
            return HTMLResponse("Forbidden", status_code=403)

        from_id = request.query_params.get("from", "")
        to_id = request.query_params.get("to", "")
        if not from_id or not to_id:
            return HTMLResponse(
                "Both 'from' and 'to' revisions are required", status_code=400
            )

        try:
            diff = await self._revision_service.diff(from_id, to_id)
        except Exception:  # noqa: BLE001 — diffing must not surface internals
            logger.exception("admin.revision_diff_failed")
            return HTMLResponse("Unable to compare revisions", status_code=503)

        if diff is None:
            return HTMLResponse("Revision not found", status_code=404)

        if not diff.fields:
            return HTMLResponse("<p>These revisions are identical.</p>")

        rows = "".join(
            f"<tr><th>{html.escape(str(entry.field_name))}</th>"
            f'<td class="old">{self._format_value(entry.old_value)}</td>'
            f'<td class="new">{self._format_value(entry.new_value)}</td></tr>'
            for entry in diff.fields
        )
        return HTMLResponse(
            "<table><thead><tr><th>Field</th><th>Before</th>"
            f"<th>After</th></tr></thead><tbody>{rows}</tbody></table>"
        )

    async def revision_revert(self, request: Request) -> Response:
        """Restore a record to a prior revision.

        The snapshot is written through the same validation and persistence
        path as a normal update, and the result is itself snapshotted, so the
        revert is an ordinary forward change that can be undone in turn.
        """
        if self._revision_service is None:
            return HTMLResponse("Revision history is not enabled", status_code=404)

        item_id = str(request.path_params.get("id", ""))
        revision_id = str(request.path_params.get("revision_id", ""))

        try:
            item = await self._load_record(item_id)
        except NotImplementedError:
            return HTMLResponse("Resource data source unavailable", status_code=503)
        except Exception:  # noqa: BLE001 — storage failures are sanitized
            logger.exception("admin.revision_revert_lookup_failed")
            return HTMLResponse("Unable to load record", status_code=503)
        if item is None:
            return HTMLResponse("Record not found", status_code=404)

        # Permission is checked against the live record, not the snapshot, so
        # revert can never be a way around the normal update authorization.
        if not await self._record_permission(request, "can_update", item):
            return HTMLResponse("This record cannot be updated", status_code=403)

        try:
            snapshot = await self._revision_service.revert_data(revision_id)
        except Exception:  # noqa: BLE001 — history failures are sanitized
            logger.exception("admin.revision_revert_lookup_failed")
            return HTMLResponse("Unable to load revision", status_code=503)
        if snapshot is None:
            return HTMLResponse("Revision not found", status_code=404)

        restorable = self._restorable(snapshot)
        if not restorable:
            return HTMLResponse(
                "Revision contains no restorable fields", status_code=422
            )

        try:
            validated = self.validate_update(
                item_id, {**self._record_mapping(item), **restorable}
            )
        except Exception:  # noqa: BLE001 — a stale snapshot may no longer be valid
            logger.info("admin.revision_revert_validation_failed")
            return HTMLResponse(
                "This revision is no longer valid for the current schema",
                status_code=422,
            )

        try:
            data_source = self.get_data_source()
            result = data_source.update(item_id, validated)
            if inspect.isawaitable(result):
                await result
        except NotImplementedError:
            return HTMLResponse("Resource does not support update", status_code=503)
        except Exception:  # noqa: BLE001 — storage failures are sanitized
            logger.exception("admin.revision_revert_failed")
            return HTMLResponse("Unable to restore revision", status_code=503)

        await self._emit_audit(
            request,
            f"{getattr(self.meta, 'name', 'resource')}.revert",
            item_id=item_id,
            new_values=validated,
        )
        # Snapshot the restored state so the revert is itself reversible.
        await self._record_revision(
            request, item_id, validated, comment=f"revert to {revision_id}"
        )

        redirect_to = self._resource_url(request, item_id)
        if request.headers.get("hx-request") == "true":
            response = Response(status_code=200)
            response.headers["HX-Redirect"] = redirect_to
            return response
        from starlette.responses import RedirectResponse

        return RedirectResponse(redirect_to, status_code=303)

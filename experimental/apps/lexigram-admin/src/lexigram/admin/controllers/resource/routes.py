"""Route registration for the resource controller."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.admin.controllers.resource import ResourceController



class ResourceRouteMixin:
    """Route registration."""

    def get_routes(self) -> list:
        """Get Starlette routes for this controller."""
        from starlette.routing import Route

        prefix = f"/{self.meta.name}"

        return [
            Route(prefix, self.list_view, methods=["GET"]),
            Route(f"{prefix}/create", self.create_form, methods=["GET"]),
            Route(prefix, self.create, methods=["POST"]),
            Route(f"{prefix}/bulk", self.bulk_action, methods=["POST"]),
            Route(
                f"{prefix}/bulk-delete-confirm",
                self.bulk_delete_confirm,
                methods=["GET"],
            ),
            Route(
                f"{prefix}/bulk-purge-confirm",
                self.bulk_purge_confirm,
                methods=["GET"],
            ),
            Route(
                f"{prefix}/bulk-restore-confirm",
                self.bulk_restore_confirm,
                methods=["GET"],
            ),
            Route(f"{prefix}/import-example", self.import_example, methods=["GET"]),
            Route(f"{prefix}/import-report", self.import_report, methods=["GET"]),
            Route(f"{prefix}/{{id}}", self.detail, methods=["GET"]),
            Route(f"{prefix}/{{id}}/edit", self.edit_form, methods=["GET"]),
            Route(
                f"{prefix}/{{id}}/delete-confirm", self.delete_confirm, methods=["GET"]
            ),
            Route(f"{prefix}/{{id}}", self.update, methods=["PUT", "POST"]),
            Route(f"{prefix}/{{id}}", self.delete, methods=["DELETE"]),
        ]

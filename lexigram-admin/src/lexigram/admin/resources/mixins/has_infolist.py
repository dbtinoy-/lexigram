"""HasInfolist mixin for resources with read-only detail entries."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from lexigram.ui import InfolistEntry


class HasInfolist:
    """Build ``InfolistEntry`` values for a record on resource detail pages.

    Uses the resource's declarative ``fields`` when set; otherwise
    derives entries from the resource ``model`` via
    ``FormSchemaGenerator``. Fields opt out via ``visible_in_view``.
    """

    def infolist(self, record: Mapping[str, Any]) -> list[InfolistEntry]:
        """Build infolist entries for a record.

        Args:
            record: Flat record mapping (``model_dump()`` shape).

        Returns:
            Entries for the fields visible in the detail view.
        """
        return [
            field.render_infolist_entry(record[field.name])
            for field in self._infolist_fields()
            if getattr(field, "visible_in_view", True) and field.name in record
        ]

    def _infolist_fields(self) -> list[Any]:
        fields = getattr(self, "fields", None)
        if fields:
            return list(fields)
        model = getattr(self, "model", None)
        if model is None:
            return []
        from lexigram.admin.forms.components import FormSchemaGenerator

        return list(FormSchemaGenerator().from_pydantic(model).fields)


__all__ = ["HasInfolist"]

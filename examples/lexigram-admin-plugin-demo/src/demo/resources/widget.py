from __future__ import annotations

from lexigram.admin.resources.base import Resource
from lexigram.admin.schema import BooleanField, DateField, SelectField, TextField


class WidgetResource(Resource):
    model = None
    name = "widgets"
    cluster = "plugins"
    icon = "box"

    fields = [
        TextField(name="title", required=True, sortable=True, searchable=True),
        SelectField(
            name="status",
            options={"active": "Active", "inactive": "Inactive", "archived": "Archived"},
            default="active",
            sortable=True,
        ),
        BooleanField(name="is_featured", label="Featured"),
        DateField(name="created_at", sortable=True),
    ]

    search_fields = ["title"]

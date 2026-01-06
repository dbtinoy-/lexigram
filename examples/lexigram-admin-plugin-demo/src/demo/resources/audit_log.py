from __future__ import annotations

from lexigram.admin.resources.base import Resource
from lexigram.admin.schema import DateField, SelectField, TextField


class AuditLogResource(Resource):
    model = None
    name = "audit_logs"
    cluster = "plugins"
    icon = "file-text"

    fields = [
        TextField(name="action", required=True, sortable=True, searchable=True),
        TextField(name="user", sortable=True),
        TextField(name="target", sortable=True),
        SelectField(
            name="severity",
            options={"info": "Info", "warning": "Warning", "error": "Error"},
            default="info",
            sortable=True,
        ),
        DateField(name="timestamp", sortable=True),
    ]

    search_fields = ["action", "user", "target"]

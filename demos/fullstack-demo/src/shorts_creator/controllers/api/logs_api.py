from lexigram.web import Controller, HTMLContent, get

from shorts_creator.services.log_store import LogStore


class LogsApiController(Controller):
    def __init__(self, log_store: LogStore):
        self.log_store = log_store

    @get("/api/logs")
    async def list_logs(self, request=None) -> HTMLContent:
        since = ""
        if request:
            since = request.query_params.get("since", "")
        entries = self.log_store.recent(since or None)
        rows = []
        for e in entries:
            css = {
                "info": "lp-info",
                "progress": "lp-progress",
                "connected": "lp-connected",
                "complete": "lp-success",
                "success": "lp-success",
                "failed": "lp-error",
                "error": "lp-error",
            }.get(e["type"], "lp-info")
            rows.append(
                f'<div class="lp-entry {css}">'
                f'<span class="lp-time">{e["time"][11:19]}</span>'
                f'<span class="lp-op">{e["op_id"][:20]}</span>'
                f'<span class="lp-msg">{e["message"]}</span>'
                f"</div>"
            )
        return HTMLContent("".join(rows))

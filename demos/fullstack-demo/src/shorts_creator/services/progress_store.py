from shorts_creator.services.log_store import LogStore
from shorts_creator.services.render_progress import RenderProgressStore


class ProgressStore(RenderProgressStore):
    def __init__(self, log_store: LogStore | None = None):
        super().__init__()
        self.log_store = log_store

    def push(self, op_id: str, event: dict) -> None:
        super().push(op_id, event)
        if self.log_store:
            ev_type = event.get("event", "message") or "message"
            msg = ""
            try:
                data = event.get("data", {}) or {}
                msg = (
                    data.get("message", "") or data.get("stage", "") or data.get("error", "") or ""
                )
            except (AttributeError, TypeError):
                msg = ""
            if msg:
                self.log_store.push(op_id, ev_type, msg)

    def create_queue(self, op_id: str) -> None:
        super().create_queue(op_id)
        if self.log_store:
            self.log_store.push(op_id, "info", f"Operation started: {op_id}")

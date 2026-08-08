from datetime import UTC, datetime


class LogStore:
    def __init__(self, max_entries: int = 200):
        self._entries: list[dict] = []
        self._max = max_entries

    def push(self, op_id: str, event_type: str, message: str) -> None:
        self._entries.append(
            {
                "time": datetime.now(UTC).isoformat(),
                "op_id": op_id,
                "type": event_type,
                "message": message,
            }
        )
        if len(self._entries) > self._max:
            self._entries = self._entries[-self._max :]

    def recent(self, since: str | None = None) -> list[dict]:
        if not since:
            return list(self._entries)
        return [e for e in self._entries if e["time"] > since]

    def clear(self) -> None:
        self._entries.clear()

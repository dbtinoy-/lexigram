"""HistoryService — persists and retrieves past pipeline runs."""

import json
import os
from datetime import UTC, datetime
from pathlib import Path
from typing import Any


class HistoryService:
    """File-based run history. Each run is a JSON file in the runs/ directory.

    In a future phase this will be replaced by lexigram-sql + SQLite.
    """

    def __init__(self, data_dir: str | None = None) -> None:
        if data_dir is None:
            data_dir = str(Path(__file__).resolve().parents[3] / "data" / "runs")
        self._data_dir = data_dir
        os.makedirs(self._data_dir, exist_ok=True)

    async def record_run(self, run_data: dict[str, Any]) -> str:
        run_id = run_data.pop("run_id", None) or datetime.now(UTC).strftime("run_%Y%m%d_%H%M%S_%f")
        run_data["run_id"] = run_id
        run_data["created_at"] = datetime.now(UTC).isoformat()
        path = os.path.join(self._data_dir, f"{run_id}.json")
        with open(path, "w") as f:
            json.dump(run_data, f, indent=2, default=str)
        return run_id

    async def get_recent(self, limit: int = 10) -> list[dict[str, Any]]:
        if not os.path.isdir(self._data_dir):
            return []
        files = sorted(
            (f for f in os.listdir(self._data_dir) if f.endswith(".json")),
            reverse=True,
        )[:limit]
        runs = []
        for fname in files:
            with open(os.path.join(self._data_dir, fname)) as f:
                runs.append(json.load(f))
        return runs

    async def get_run(self, run_id: str) -> dict[str, Any] | None:
        path = os.path.join(self._data_dir, f"{run_id}.json")
        if not os.path.exists(path):
            return None
        with open(path) as f:
            return json.load(f)

    async def update_run(self, run_id: str, updates: dict[str, Any]) -> bool:
        path = os.path.join(self._data_dir, f"{run_id}.json")
        if not os.path.exists(path):
            return False
        with open(path) as f:
            data = json.load(f)
        data.update(updates)
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        return True

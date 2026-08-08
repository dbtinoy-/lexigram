import pytest

from shorts_creator.controllers.api.logs_api import LogsApiController
from shorts_creator.services.log_store import LogStore


class TestLogsApi:
    @pytest.mark.asyncio
    async def test_list_logs_returns_html(self):
        store = LogStore()
        store.push("op1", "info", "hello")
        store.push("op2", "complete", "done")
        ctrl = LogsApiController(store)
        resp = await ctrl.list_logs()
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert "lp-entry" in body
        assert "hello" in body
        assert "done" in body

    @pytest.mark.asyncio
    async def test_list_logs_empty(self):
        store = LogStore()
        ctrl = LogsApiController(store)
        resp = await ctrl.list_logs()
        body = resp.body if hasattr(resp, "body") else str(resp)
        assert body == ""

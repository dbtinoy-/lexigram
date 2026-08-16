from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.nosql.cli.checks import check_nosql_connection


class TestCheckNosqlConnection:
    @pytest.mark.asyncio
    async def test_returns_ok_status(self) -> None:
        container = MagicMock()
        result = await check_nosql_connection(container)
        assert result == {"status": "ok", "message": "NoSQL health check not yet implemented"}

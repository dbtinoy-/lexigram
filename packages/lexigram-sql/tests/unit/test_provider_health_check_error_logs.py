import pytest
from unittest.mock import patch

from lexigram.sql.providers import DatabaseService


class BadProvider:
    async def health_check(self):
        raise RuntimeError("boom")


@pytest.mark.asyncio
async def test_health_check_logs_and_returns_unhealthy():
    provider = DatabaseService("sqlite:///:memory:")
    provider.db_provider = BadProvider()

    with patch("lexigram.sql.providers._health_mixin.logger") as mock_logger:
        res = await provider.health_check()

    assert res.status.value == "unhealthy"
    assert any(
        "DatabaseService.health_check encountered error" in call.args[0]
        for call in mock_logger.error.call_args_list
    )


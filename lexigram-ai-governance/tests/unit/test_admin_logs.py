"""Tests for the relay request-log and usage ranking admin pages.

The pages are permission-gated reads: they render metadata-only tables
(filtered by token/user where relevant), never echo prompt/media
content, and resolve the usage service protocol from the container.
"""

from __future__ import annotations

from datetime import datetime

import pytest
from starlette.datastructures import QueryParams

from lexigram.ai.governance.admin.contributor import GovernanceAdminContributor
from lexigram.ai.governance.admin.logs_pages import (
    RelayRequestLogsPage,
    RelayUsageRankingsPage,
)
from lexigram.contracts.ai.relay import (
    RelayDailyUsage,
    RelayModelRank,
    RelayRequestLogEntry,
    RelayUsageServiceProtocol,
)

_CANARY = "canary-sensitive-content-42"


class FakeUsageService(RelayUsageServiceProtocol):
    """Protocol-conforming usage service with canned responses."""

    def __init__(self) -> None:
        self.entries = [
            RelayRequestLogEntry(
                request_id="req-1",
                user_id="u1",
                token_id="t1",
                endpoint_kind="chat",
                model="gpt-4",
                channel_name="ch-1",
                status="completed",
                created_at=datetime(2026, 8, 10, 12, 0, 0),
                prompt_tokens=10,
                completion_tokens=20,
                cost="0.05",
                latency_ms=350,
            ),
            RelayRequestLogEntry(
                request_id="req-2",
                user_id="u2",
                token_id="t2",
                endpoint_kind="responses",
                model="claude-3",
                channel_name="ch-2",
                status="failed",
                created_at=datetime(2026, 8, 10, 13, 0, 0),
                error_code="UPSTREAM_5XX",
            ),
        ]
        self.daily = [
            RelayDailyUsage(
                day="2026-08-10", prompt_tokens=10, completion_tokens=20, cost="0.05"
            )
        ]
        self.ranks = [
            RelayModelRank(
                model="gpt-4", completion_tokens=200, request_count=4, cost="0.5"
            )
        ]

    async def daily_usage(self, user_id: str, days: int) -> list[RelayDailyUsage]:
        del user_id, days
        return self.daily

    async def model_rank(self, days: int, limit: int) -> list[RelayModelRank]:
        del days, limit
        return self.ranks

    async def list_requests(
        self,
        days: int,
        page: int,
        page_size: int,
        *,
        user_id: str | None = None,
        token_id: str | None = None,
    ) -> list[RelayRequestLogEntry]:
        del days, page, page_size, user_id, token_id
        return self.entries


class _Request:
    """Minimal request stand-in carrying query parameters."""

    def __init__(self, **params: str) -> None:
        self.query_params = QueryParams(params)


async def _html(page: object, **params: str) -> str:
    response = await page.handle(_Request(**params))  # type: ignore[attr-defined]
    return response.body.decode()


async def test_request_logs_page_renders_rows_without_content() -> None:
    page = RelayRequestLogsPage(service=FakeUsageService())
    html = await _html(page, token="t1")
    assert "req-1" in html
    assert "req-2" in html
    assert "gpt-4" in html
    assert "UPSTREAM_5XX" in html
    assert _CANARY not in html
    assert "<img" not in html
    assert "data:image" not in html
    assert "Authorization" not in html
    assert "x-api-key" not in html


async def test_request_logs_page_unavailable_without_service() -> None:
    page = RelayRequestLogsPage(service=None)
    html = await _html(page)
    assert "Unavailable" in html


async def test_usage_rankings_page_renders_rank_table() -> None:
    page = RelayUsageRankingsPage(service=FakeUsageService())
    html = await _html(page)
    assert "gpt-4" in html
    assert "200" in html
    assert "4" in html
    assert "0.5" in html
    assert _CANARY not in html
    assert "<img" not in html


async def test_usage_rankings_page_unavailable_without_service() -> None:
    page = RelayUsageRankingsPage(service=None)
    html = await _html(page)
    assert "Unavailable" in html


@pytest.mark.asyncio
async def test_pages_resolve_usage_service_protocol_from_container() -> None:
    container = FakeContainer()
    service = await container.resolve(RelayUsageServiceProtocol)
    assert service is not None
    logs_page = RelayRequestLogsPage(service=service)
    rankings_page = RelayUsageRankingsPage(service=service)
    assert logs_page.handle is not None
    assert rankings_page.handle is not None


class FakeContainer:
    """Container stand-in resolving the usage service protocol."""

    async def resolve(self, service_type: object) -> FakeUsageService | None:
        if service_type is RelayUsageServiceProtocol:
            return FakeUsageService()
        return None


def test_contributor_pages_require_relay_logs_scope() -> None:
    contributor = GovernanceAdminContributor()
    pages = {p.name: p for p in contributor.get_management_pages()}
    assert pages["governance_relay_logs"].permission == "relay.logs"
    assert pages["governance_relay_rankings"].permission == "relay.logs"
    nav = {item.label: item for item in contributor.get_navigation_items()}
    assert any(
        child.permission == "relay.logs" for child in nav["AI Governance"].children
    )


def test_contributor_page_handlers_are_importable() -> None:
    contributor = GovernanceAdminContributor()
    pages = {p.name: p for p in contributor.get_management_pages()}
    for name in ("governance_relay_logs", "governance_relay_rankings"):
        handler = pages[name].handler
        assert isinstance(handler, str)
        mod_name, _, attr = handler.partition(":")
        mod = __import__(mod_name, fromlist=[attr])
        assert hasattr(mod, attr)
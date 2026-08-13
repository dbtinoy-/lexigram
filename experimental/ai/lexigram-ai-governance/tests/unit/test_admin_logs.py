"""Tests for the relay request-log and usage ranking admin pages.

The pages are permission-gated reads: they render metadata-only tables
(filtered by token/user where relevant), never echo prompt/media
content, and resolve the usage service protocol from the container.
"""

from __future__ import annotations

from datetime import datetime

from lexigram.ai.governance.admin.contributor import GovernanceAdminContributor
from lexigram.ai.governance.admin.logs_pages import (
    RelayRequestLogsPage,
    RelayUsageRankingsPage,
)
from lexigram.contracts.admin import PageContent
from lexigram.contracts.admin.widget_content import EmptyContent, TableContent
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


class FakeUrl:
    """Minimal URL stand-in with a string form."""

    path = "/admin/ai-governance/relay-logs"

    def __str__(self) -> str:
        return "http://testserver/admin/ai-governance/relay-logs"


class FakeRequest:
    """Minimal ASGI request stand-in with query params and a URL."""

    query_params: dict[str, str] = {}
    url: FakeUrl = FakeUrl()

    @classmethod
    def with_params(cls, **params: str) -> FakeRequest:
        request = cls()
        request.query_params = params
        return request


def _cells(content: PageContent) -> list[str]:
    assert isinstance(content.body, TableContent)
    return [cell.text for row in content.body.rows for cell in row]


async def test_request_logs_page_renders_rows_without_content() -> None:
    page = RelayRequestLogsPage(service=FakeUsageService())
    content = await page.handle(FakeRequest.with_params(token="t1"))
    assert isinstance(content, PageContent)
    assert content.title == "Request Logs"
    cells = _cells(content)
    assert "req-1" in cells
    assert "req-2" in cells
    assert "gpt-4" in cells
    assert "UPSTREAM_5XX" in cells
    assert _CANARY not in cells
    assert content.pagination is not None
    assert content.pagination.page == 1
    assert content.pagination.total == 2
    assert content.pagination.per_page == 20
    assert (
        content.pagination.base_url
        == "http://testserver/admin/ai-governance/relay-logs"
    )


async def test_request_logs_page_unavailable_without_service() -> None:
    page = RelayRequestLogsPage(service=None)
    content = await page.handle(FakeRequest())
    assert isinstance(content, PageContent)
    assert content.title == "Request Logs"
    assert isinstance(content.body, EmptyContent)
    assert content.body.title == "Unavailable"


async def test_usage_rankings_page_renders_rank_table() -> None:
    page = RelayUsageRankingsPage(service=FakeUsageService())
    content = await page.handle(FakeRequest())
    assert isinstance(content, PageContent)
    assert content.title == "Usage Rankings"
    cells = _cells(content)
    assert "gpt-4" in cells
    assert "200" in cells
    assert "4" in cells
    assert "0.5" in cells
    assert _CANARY not in cells
    assert content.pagination is None


async def test_usage_rankings_page_unavailable_without_service() -> None:
    page = RelayUsageRankingsPage(service=None)
    content = await page.handle(FakeRequest())
    assert isinstance(content, PageContent)
    assert content.title == "Usage Rankings"
    assert isinstance(content.body, EmptyContent)
    assert content.body.title == "Unavailable"


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

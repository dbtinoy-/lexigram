"""Tests for the relay ledger admin page and actions.

The ledger surfaces are permission-gated under ``relay.billing``:
two admin actions (settle a top-up, run a daily check-in) that call
the ledger service protocol, and a read-only top-up list page that
renders reference/amount/status only — never keys or headers.
"""

from __future__ import annotations

import pytest
from starlette.datastructures import QueryParams

from lexigram.ai.governance.admin.contributor import GovernanceAdminContributor
from lexigram.ai.governance.admin.ledger_actions import run_checkin, settle_topup
from lexigram.ai.governance.admin.ledger_pages import RelayLedgerPage
from lexigram.contracts.ai.governance import RelayUsageScope
from lexigram.contracts.ai.relay import (
    RelayCheckinRecord,
    RelayLedgerError,
    RelayLedgerServiceProtocol,
    RelayTopUpRecord,
)
from lexigram.di.container.container import Container
from lexigram.result import Err, Ok

_CANARY = "sk-canary-secret-key"


class FakeLedger(RelayLedgerServiceProtocol):
    """Protocol-conforming ledger service with canned responses."""

    def __init__(self) -> None:
        self.settle_calls: list[tuple[str, str]] = []
        self.checkin_calls: list[tuple[str, str]] = []
        self.settle_error: RelayLedgerError | None = None
        self.checkin_error: RelayLedgerError | None = None
        self.topups: list[RelayTopUpRecord] = []

    async def credit(
        self, scope: RelayUsageScope, amount: str, reason: str
    ) -> object:
        del scope, amount, reason
        return Ok(None)

    async def settle_topup(
        self, reference_id: str, expected_status: str
    ) -> object:
        self.settle_calls.append((reference_id, expected_status))
        if self.settle_error is not None:
            return Err(self.settle_error)
        return Ok(None)

    async def checkin(self, user_id: str, award: str) -> object:
        self.checkin_calls.append((user_id, award))
        if self.checkin_error is not None:
            return Err(self.checkin_error)
        return Ok(
            RelayCheckinRecord(
                user_id=user_id,
                day="2026-08-10",
                award=award,
                created_at="2026-08-10T00:00:00+00:00",
            )
        )

    async def list_topups(
        self, user_id: str | None, limit: int
    ) -> list[RelayTopUpRecord]:
        del user_id, limit
        return list(self.topups)


def make_container(ledger: FakeLedger) -> Container:
    container = Container()
    container.singleton(RelayLedgerServiceProtocol, ledger)
    return container


def topup(
    reference_id: str, amount: str, status: str = "completed"
) -> RelayTopUpRecord:
    return RelayTopUpRecord(
        reference_id=reference_id,
        user_id="u1",
        amount=amount,
        status=status,
        created_at="2026-08-10T00:00:00+00:00",
    )


class _Request:
    """Minimal request stand-in carrying query parameters."""

    def __init__(self, **params: str) -> None:
        self.query_params = QueryParams(params)


async def _html(page: object, **params: str) -> str:
    response = await page.handle(_Request(**params))  # type: ignore[attr-defined]
    return response.body.decode()


def test_ledger_surfaces_require_relay_billing_scope() -> None:
    contributor = GovernanceAdminContributor()
    actions = {a.name: a for a in contributor.get_actions()}
    for name in ("settle_topup", "run_checkin"):
        assert actions[name].permission == "relay.billing"
    pages = {p.name: p for p in contributor.get_management_pages()}
    assert pages["governance_relay_ledger"].permission == "relay.billing"
    assert "relay.billing" in contributor.required_permissions


def test_ledger_action_handlers_are_importable() -> None:
    contributor = GovernanceAdminContributor()
    actions = {a.name: a for a in contributor.get_actions()}
    for name in ("settle_topup", "run_checkin"):
        handler = actions[name].handler
        mod_name, _, attr = handler.partition(":")
        mod = __import__(mod_name, fromlist=[attr])
        assert hasattr(mod, attr)


async def test_settle_topup_validates_reference() -> None:
    ledger = FakeLedger()
    container = make_container(ledger)
    result = await settle_topup(container)
    assert result["ok"] is False
    assert "reference_id" in str(result["message"])


async def test_settle_topup_calls_service_with_expected_status() -> None:
    ledger = FakeLedger()
    container = make_container(ledger)
    result = await settle_topup(container, reference_id="ref-1")
    assert result["ok"] is True
    assert ledger.settle_calls == [("ref-1", "pending")]


async def test_settle_topup_surfaces_service_error() -> None:
    ledger = FakeLedger()
    ledger.settle_error = RelayLedgerError(code="not_found", message="missing")
    container = make_container(ledger)
    result = await settle_topup(container, reference_id="ref-1")
    assert result["ok"] is False
    assert result["code"] == "not_found"
    assert "missing" in str(result["message"])


async def test_settle_topup_requires_ledger_service() -> None:
    result = await settle_topup(Container())
    assert result["ok"] is False


async def test_run_checkin_validates_params() -> None:
    ledger = FakeLedger()
    container = make_container(ledger)
    result = await run_checkin(container)
    assert result["ok"] is False
    result = await run_checkin(container, user_id="u1")
    assert result["ok"] is False
    result = await run_checkin(container, user_id="u1", award="5")
    assert result["ok"] is True
    assert ledger.checkin_calls == [("u1", "5")]


async def test_run_checkin_surfaces_duplicate_error() -> None:
    ledger = FakeLedger()
    ledger.checkin_error = RelayLedgerError(
        code="already_checked_in", message="already checked in today"
    )
    container = make_container(ledger)
    result = await run_checkin(container, user_id="u1", award="5")
    assert result["ok"] is False
    assert result["code"] == "already_checked_in"


async def test_ledger_page_renders_topup_rows() -> None:
    ledger = FakeLedger()
    ledger.topups = [topup("ref-1", "100.00"), topup("ref-2", "25", "pending")]
    page = RelayLedgerPage(service=ledger)
    html = await _html(page)
    assert "ref-1" in html
    assert "ref-2" in html
    assert "100.00" in html
    assert "pending" in html
    assert _CANARY not in html
    assert "Authorization" not in html


async def test_ledger_page_empty_state() -> None:
    page = RelayLedgerPage(service=FakeLedger())
    html = await _html(page)
    assert "No top-ups" in html


async def test_ledger_page_unavailable_without_service() -> None:
    page = RelayLedgerPage(service=None)
    html = await _html(page)
    assert "Unavailable" in html
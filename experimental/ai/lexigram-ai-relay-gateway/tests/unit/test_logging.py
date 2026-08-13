"""Tests for the relay request-log emitter (entry builder + fire-and-forget)."""

from __future__ import annotations

import asyncio
from datetime import datetime
from typing import Any

from starlette.requests import Request

from lexigram.ai.relay.gateway.logging import RelayRequestLogger
from lexigram.ai.relay.gateway.web.routes import (
    _with_auth_guard,
    relay_endpoint,
)
from lexigram.ai.relay.gateway.web.shared import log_request
from lexigram.contracts.ai.relay import (
    RelayAuthIdentity,
    RelayFormat,
    RelayGatewayError,
    RelayGatewayRequest,
    RelayGatewayResult,
    RelayRequestLogEntry,
    RelayRequestLogStoreProtocol,
)
from lexigram.contracts.ai.relay.gateway import RelayGatewayErrorCode
from lexigram.contracts.core.result import Err, Ok, Result


class FakeStore:
    """``RelayRequestLogStoreProtocol`` double recording appended entries."""

    def __init__(self, *, raise_on_append: bool = False) -> None:
        self.entries: list[RelayRequestLogEntry] = []
        self.raise_on_append = raise_on_append

    async def append(self, entry: RelayRequestLogEntry) -> None:
        if self.raise_on_append:
            raise RuntimeError("store down")
        self.entries.append(entry)


class FakeGateway:
    """``RelayGatewayProtocol`` double with a canned result."""

    def __init__(self, *, ok: bool = True) -> None:
        self.ok = ok

    async def handle(
        self, request: RelayGatewayRequest
    ) -> Result[RelayGatewayResult, RelayGatewayError]:
        if not self.ok:
            return Err(
                RelayGatewayError(
                    code=RelayGatewayErrorCode.UPSTREAM_ERROR,
                    message="upstream 500",
                    status_code=502,
                    request_id=request.request_id,
                )
            )
        return Ok(RelayGatewayResult(status_code=200, headers={}, payload={}))


class FakeContainer:
    """Container double resolving the log store binding."""

    def __init__(self, store: FakeStore | None) -> None:
        self._store = store

    async def resolve_optional(self, service_type: type[Any]) -> Any | None:
        if service_type is RelayRequestLogStoreProtocol:
            return self._store
        return None


def _resolve_gateway(*, ok: bool = True) -> Any:
    """Resolve a fake gateway through the resolver protocol."""

    async def resolver(request: Request) -> FakeGateway:
        return FakeGateway(ok=ok)

    return resolver


async def _make_request() -> Request:
    async def receive() -> dict[str, Any]:
        return {
            "type": "http.request",
            "body": b'{"model": "gpt-4"}',
            "more_body": False,
        }

    return Request(
        {
            "type": "http",
            "method": "POST",
            "path": "/v1/chat/completions",
            "headers": [],
        },
        receive=receive,
    )


async def test_buffered_request_records_exactly_one_entry() -> None:
    store = FakeStore()
    request = await _make_request()
    request.state.container = FakeContainer(store)
    guarded = _with_auth_guard(
        lambda req: relay_endpoint(RelayFormat.OPENAI_CHAT, _resolve_gateway(), req)
    )
    response = await guarded(request)
    assert response.status_code == 200
    await asyncio.sleep(0)
    assert len(store.entries) == 1
    entry = store.entries[0]
    assert entry.endpoint_kind == "chat"
    assert entry.model == "gpt-4"
    assert entry.status == "completed"
    assert entry.created_at is not None
    assert isinstance(entry.created_at, datetime)


async def test_entry_carries_identity_attribution() -> None:
    store = FakeStore()
    request = await _make_request()
    request.state.container = FakeContainer(store)
    request.state.relay_identity = RelayAuthIdentity(user_id="u7", token_id="tk7")
    guarded = _with_auth_guard(
        lambda req: relay_endpoint(RelayFormat.OPENAI_CHAT, _resolve_gateway(), req)
    )
    await guarded(request)
    await asyncio.sleep(0)
    entry = store.entries[0]
    assert entry.user_id == "u7"
    assert entry.token_id == "tk7"


async def test_failed_dispatch_records_error_code() -> None:
    store = FakeStore()
    request = await _make_request()
    request.state.container = FakeContainer(store)
    guarded = _with_auth_guard(
        lambda req: relay_endpoint(
            RelayFormat.OPENAI_CHAT, _resolve_gateway(ok=False), req
        )
    )
    response = await guarded(request)
    assert response.status_code == 502
    await asyncio.sleep(0)
    entry = store.entries[0]
    assert entry.status == "failed"
    assert entry.error_code == "UPSTREAM_ERROR"


async def test_store_failure_does_not_change_response() -> None:
    store = FakeStore(raise_on_append=True)
    request = await _make_request()
    request.state.container = FakeContainer(store)
    guarded = _with_auth_guard(
        lambda req: relay_endpoint(RelayFormat.OPENAI_CHAT, _resolve_gateway(), req)
    )
    response = await guarded(request)
    await asyncio.sleep(0)
    assert response.status_code == 200


async def test_no_store_means_no_entry() -> None:
    request = await _make_request()
    request.state.container = FakeContainer(store=None)
    guarded = _with_auth_guard(
        lambda req: relay_endpoint(RelayFormat.OPENAI_CHAT, _resolve_gateway(), req)
    )
    response = await guarded(request)
    assert response.status_code == 200
    await asyncio.sleep(0)


async def test_background_tasks_retains_reference_until_done() -> None:
    release = asyncio.Event()

    class BlockingStore:
        async def append(self, entry: RelayRequestLogEntry) -> None:
            await release.wait()

    logger = RelayRequestLogger(store=BlockingStore())
    logger.log(
        RelayRequestLogEntry(
            request_id="r1",
            user_id="",
            token_id="",
            endpoint_kind="chat",
            model="gpt-4",
            channel_name="",
            status="completed",
            created_at=datetime(2026, 8, 10, 12, 0, 0),
        )
    )
    assert len(logger._background_tasks) == 1
    release.set()
    task = next(iter(logger._background_tasks))
    await task
    assert len(logger._background_tasks) == 0


async def test_log_request_builds_entry_directly() -> None:
    store = FakeStore()
    request = await _make_request()
    request.state.relay_identity = RelayAuthIdentity(user_id="u1", token_id="t1")
    log_request(
        request,
        RelayRequestLogger(store=store),
        kind="chat",
        status="completed",
        model="gpt-4",
        latency_ms=12,
    )
    await asyncio.sleep(0)
    entry = store.entries[0]
    assert entry.user_id == "u1"
    assert entry.token_id == "t1"
    assert entry.latency_ms == 12

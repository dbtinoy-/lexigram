"""Tests for PreviewService lifecycle and event fan-out (fake spawner)."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from lexigram.builder.services.preview import PreviewService


class FakeServer:
    def __init__(self, pid: int, healthy_process: bool = True) -> None:
        self._pid = pid
        self.terminated = False
        self._healthy_process = healthy_process

    @property
    def pid(self) -> int:
        return self._pid

    def terminate(self) -> None:
        self.terminated = True
        self._healthy_process = False

    def is_running(self) -> bool:
        return self._healthy_process


class FakeSpawner:
    def __init__(self, server: FakeServer | Exception) -> None:
        self._server_or_exc = server
        self.started_with: list[list[str]] = []

    async def start(self, command: list[str], *, cwd: Path) -> FakeServer:
        self.started_with.append(command)
        if isinstance(self._server_or_exc, Exception):
            raise self._server_or_exc
        return self._server_or_exc


def make_service(
    tmp_path: Path,
    *,
    health_ok: bool = True,
    server: FakeServer | None = None,
) -> tuple[PreviewService, FakeSpawner, FakeServer]:
    spawner = FakeSpawner(server or FakeServer(pid=4242))
    svc = PreviewService(
        spawner,  # type: ignore[arg-type]
        health_check=lambda url: health_ok,
        poll_interval=0.01,
        heartbeat_interval=0.05,
    )
    return svc, spawner, spawner._server_or_exc  # type: ignore[return-value]


async def test_start_returns_info_and_publishes_live(tmp_path: Path) -> None:
    svc, _spawner, _srv = make_service(tmp_path)
    events: asyncio.Queue[dict] = svc.subscribe()

    result = await svc.start(
        "alpha",
        command=["uvicorn"],
        cwd=tmp_path,
        port=8101,
    )

    assert result.is_ok()
    info = result.unwrap()
    assert info.pid == 4242
    assert svc.port_of("alpha") == 8101
    seen = await asyncio.wait_for(events.get(), timeout=1)
    assert seen["type"] == "phase"
    assert seen["phase"] == "live"


async def test_unhealthy_server_times_out_and_terminates(tmp_path: Path) -> None:
    svc, _spawner, srv = make_service(
        tmp_path, health_ok=False
    )
    result = await svc.start(
        "alpha", command=["uvicorn"], cwd=tmp_path, port=8102
    )
    assert result.is_err()
    assert srv.terminated is True


async def test_stop_is_idempotent_and_terminates_once(tmp_path: Path) -> None:
    svc, _spawner, srv = make_service(tmp_path)
    await svc.start("alpha", command=["uvicorn"], cwd=tmp_path, port=8103)

    await svc.stop("alpha")
    await svc.stop("alpha")

    assert srv.terminated is True
    assert svc.info("alpha") is None


@pytest.mark.parametrize("spawn_raises", [True])
async def test_spawn_failure_maps_to_err(tmp_path: Path, spawn_raises: bool) -> None:
    spawner = FakeSpawner(RuntimeError("boom"))
    svc = PreviewService(
        spawner,  # type: ignore[arg-type]
        health_check=lambda url: True,
    )
    result = await svc.start("x", command=[], cwd=tmp_path, port=9)
    assert result.is_err()
    assert "boom" in str(result.unwrap_err())


async def test_event_fan_out_reaches_all_subscribers(tmp_path: Path) -> None:
    svc, _spawner, _srv = make_service(tmp_path)
    queue_a: asyncio.Queue[dict] = svc.subscribe()
    queue_b: asyncio.Queue[dict] = svc.subscribe()

    svc.publish({"type": "log", "line": "hello"})

    got_a = await asyncio.wait_for(queue_a.get(), timeout=1)
    got_b = await asyncio.wait_for(queue_b.get(), timeout=1)
    assert got_a == got_b == {"type": "log", "line": "hello"}


async def test_heartbeat_pings_while_subscribed(tmp_path: Path) -> None:
    svc, _spawner, _srv = make_service(tmp_path)
    events: asyncio.Queue[dict] = svc.subscribe()
    try:
        event = await asyncio.wait_for(events.get(), timeout=1)
        assert event == {"type": "ping"}
    finally:
        svc.unsubscribe(events)

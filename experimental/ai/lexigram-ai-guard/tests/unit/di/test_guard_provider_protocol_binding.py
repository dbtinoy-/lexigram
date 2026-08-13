"""GuardProvider must register GuardPipelineProtocol so agents can resolve it (D2)."""

from __future__ import annotations

import pytest

from lexigram.contracts.ai.guards import GuardPipelineProtocol


class _Recorder:
    def __init__(self) -> None:
        self.singletons: list[tuple[object, object]] = []

    def singleton(self, token: object, impl: object) -> None:
        self.singletons.append((token, impl))


@pytest.mark.asyncio
async def test_enabled_branch_binds_protocol_token() -> None:
    from lexigram.ai.guard.di.provider import GuardProvider

    provider = GuardProvider()
    recorder = _Recorder()
    await provider.register(recorder)  # type: ignore[arg-type]

    protocol_entries = [
        (token, impl)
        for token, impl in recorder.singletons
        if token is GuardPipelineProtocol
    ]
    assert len(protocol_entries) == 1
    assert protocol_entries[0][1] is provider._pipeline


@pytest.mark.asyncio
async def test_disabled_branch_binds_protocol_token() -> None:
    from lexigram.ai.guard.config import GuardConfig
    from lexigram.ai.guard.di.provider import GuardProvider

    provider = GuardProvider(config=GuardConfig(enabled=False))
    recorder = _Recorder()
    await provider.register(recorder)  # type: ignore[arg-type]

    protocol_entries = [
        (token, impl)
        for token, impl in recorder.singletons
        if token is GuardPipelineProtocol
    ]
    assert len(protocol_entries) == 1
    assert protocol_entries[0][1] is provider._pipeline
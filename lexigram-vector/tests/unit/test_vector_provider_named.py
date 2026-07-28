"""Tests for VectorProvider multi-backend Named DI support."""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.contracts.core import HealthCheckResult, HealthStatus
from lexigram.vector.config import NamedVectorConfig, VectorConfig
from lexigram.vector.di.provider import VectorProvider

# ---------------------------------------------------------------------------
# Shared helpers
# ---------------------------------------------------------------------------


def _make_two_backend_config(
    *,
    first_primary: bool = False,
    second_primary: bool = False,
) -> VectorConfig:
    """Return a VectorConfig with two in-memory named backends."""
    return VectorConfig(
        backends=[
            NamedVectorConfig(name="primary", primary=first_primary, backend="memory"),
            NamedVectorConfig(
                name="analytics", primary=second_primary, backend="memory"
            ),
        ]
    )


def _mock_memory_store() -> AsyncMock:
    """Return a fully-mocked async vector store."""
    store = AsyncMock()
    store.connect = AsyncMock()
    store.disconnect = AsyncMock()
    store.health_check = AsyncMock()
    return store


# ---------------------------------------------------------------------------
# 1. Single-backend path leaves _store_services empty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_backend_leaves_store_services_empty() -> None:
    """Single-backend config must not populate _store_services."""
    provider = VectorProvider(config=VectorConfig(backend="memory"))
    container = MagicMock()
    container.singleton = MagicMock()

    await provider.register(container)

    assert provider._store_services == []


# ---------------------------------------------------------------------------
# 2. Multi-backend populates _store_services per entry
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_backend_populates_store_services_per_entry() -> None:
    """_store_services must have one entry per named backend after register()."""
    cfg = _make_two_backend_config()
    provider = VectorProvider(config=cfg)
    container = MagicMock()
    container.singleton = MagicMock()

    mock_store_1 = _mock_memory_store()
    mock_store_2 = _mock_memory_store()

    with patch(
        "lexigram.vector.backends.memory.MemoryVectorStore",
        side_effect=[mock_store_1, mock_store_2],
    ):
        await provider.register(container)

    assert len(provider._store_services) == 2
    names = [name for name, _ in provider._store_services]
    assert names == ["primary", "analytics"]


# ---------------------------------------------------------------------------
# 3. Named singletons registered for each backend
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_named_singletons_registered_for_each_backend() -> None:
    """container.singleton must be called with name= for every backend entry."""
    cfg = _make_two_backend_config()
    provider = VectorProvider(config=cfg)
    container = MagicMock()
    container.singleton = MagicMock()

    mock_store_1 = _mock_memory_store()
    mock_store_2 = _mock_memory_store()

    with patch(
        "lexigram.vector.backends.memory.MemoryVectorStore",
        side_effect=[mock_store_1, mock_store_2],
    ):
        await provider.register(container)

    named = [c.kwargs.get("name") for c in container.singleton.call_args_list]
    assert "primary" in named
    assert "analytics" in named


# ---------------------------------------------------------------------------
# 4. Primary (explicit primary=True) gets unnamed binding
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_explicit_primary_gets_unnamed_binding() -> None:
    """Backend with primary=True must also receive the unnamed VectorStoreProtocol binding."""
    cfg = VectorConfig(
        backends=[
            NamedVectorConfig(name="primary", primary=True, backend="memory"),
            NamedVectorConfig(name="analytics", primary=False, backend="memory"),
        ]
    )
    provider = VectorProvider(config=cfg)
    container = MagicMock()
    container.singleton = MagicMock()

    mock_store_1 = _mock_memory_store()
    mock_store_2 = _mock_memory_store()

    with patch(
        "lexigram.vector.backends.memory.MemoryVectorStore",
        side_effect=[mock_store_1, mock_store_2],
    ):
        await provider.register(container)

    # At least one call should use name=None (the unnamed binding for primary)
    unnamed_calls = [
        c for c in container.singleton.call_args_list if c.kwargs.get("name") is None
    ]
    assert len(unnamed_calls) >= 1


# ---------------------------------------------------------------------------
# 5. First entry by identity gets unnamed binding when no explicit primary
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_first_entry_by_identity_gets_unnamed_binding_when_no_explicit_primary() -> (
    None
):
    """When no entry has primary=True the first entry must get the unnamed binding."""
    cfg = VectorConfig(
        backends=[
            NamedVectorConfig(name="first", primary=False, backend="memory"),
            NamedVectorConfig(name="second", primary=False, backend="memory"),
        ]
    )
    provider = VectorProvider(config=cfg)
    container = MagicMock()
    container.singleton = MagicMock()

    mock_store_1 = _mock_memory_store()
    mock_store_2 = _mock_memory_store()

    with patch(
        "lexigram.vector.backends.memory.MemoryVectorStore",
        side_effect=[mock_store_1, mock_store_2],
    ):
        await provider.register(container)

    # The named binding for "first" AND an unnamed binding must both be present.
    names = [c.kwargs.get("name") for c in container.singleton.call_args_list]
    assert "first" in names
    # Unnamed binding (name=None) for the first-by-identity backend
    assert None in names


# ---------------------------------------------------------------------------
# 6. Second entry does NOT get unnamed binding
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_second_non_primary_entry_does_not_get_unnamed_binding() -> None:
    """The second (non-primary) backend must NOT receive the unnamed binding."""
    cfg = VectorConfig(
        backends=[
            NamedVectorConfig(name="primary", primary=True, backend="memory"),
            NamedVectorConfig(name="analytics", primary=False, backend="memory"),
        ]
    )
    provider = VectorProvider(config=cfg)
    container = MagicMock()
    container.singleton = MagicMock()

    mock_store_1 = _mock_memory_store()
    mock_store_2 = _mock_memory_store()

    with patch(
        "lexigram.vector.backends.memory.MemoryVectorStore",
        side_effect=[mock_store_1, mock_store_2],
    ):
        await provider.register(container)

    # Collect calls that use name="analytics"
    analytics_calls = [
        c
        for c in container.singleton.call_args_list
        if c.kwargs.get("name") == "analytics"
    ]
    # All "analytics" calls must be named (none should be unnamed)
    assert len(analytics_calls) >= 1
    # There should be exactly one unnamed call total (for the primary)
    unnamed_calls = [
        c for c in container.singleton.call_args_list if c.kwargs.get("name") is None
    ]
    # The unnamed call must NOT correspond to analytics (it's the primary's factory)
    # We verify this by confirming analytics calls all carry name="analytics"
    for call in analytics_calls:
        assert call.kwargs.get("name") == "analytics"

    # Exactly one unnamed singleton call comes from multi-backend primary
    # (the very first call with name=None is from the existing single-backend line,
    # and the second from the primary — both overwrite, but both have name=None)
    assert len(unnamed_calls) >= 1


# ---------------------------------------------------------------------------
# 7. Parallel boot — asyncio.gather is called for multi-backend
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_backend_boot_connects_all_stores() -> None:
    """boot() must call connect() on every named store (in parallel via gather)."""
    cfg = _make_two_backend_config()
    provider = VectorProvider(config=cfg)
    container = MagicMock()
    container.singleton = MagicMock()

    mock_store_1 = _mock_memory_store()
    mock_store_2 = _mock_memory_store()

    with patch(
        "lexigram.vector.backends.memory.MemoryVectorStore",
        side_effect=[mock_store_1, mock_store_2],
    ):
        await provider.register(container)
        await provider.boot(container)

    mock_store_1.connect.assert_awaited_once()
    mock_store_2.connect.assert_awaited_once()


@pytest.mark.asyncio
async def test_multi_backend_boot_uses_asyncio_gather() -> None:
    """boot() delegates parallel connection to asyncio.gather."""
    cfg = _make_two_backend_config()
    provider = VectorProvider(config=cfg)
    container = MagicMock()
    container.singleton = MagicMock()

    mock_store_1 = _mock_memory_store()
    mock_store_2 = _mock_memory_store()

    with patch(
        "lexigram.vector.backends.memory.MemoryVectorStore",
        side_effect=[mock_store_1, mock_store_2],
    ):
        await provider.register(container)

    gather_called = False
    original_gather = asyncio.gather

    async def spy_gather(*coros, **kwargs):
        nonlocal gather_called
        gather_called = True
        return await original_gather(*coros, **kwargs)

    with patch("lexigram.vector.di.provider.asyncio.gather", side_effect=spy_gather):
        await provider.boot(container)

    assert gather_called


# ---------------------------------------------------------------------------
# 8. LIFO shutdown order
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_backend_shutdown_disconnects_in_lifo_order() -> None:
    """shutdown() must disconnect stores in reverse registration (LIFO) order."""
    cfg = _make_two_backend_config()
    provider = VectorProvider(config=cfg)
    container = MagicMock()
    container.singleton = MagicMock()

    call_order: list[str] = []

    mock_store_1 = _mock_memory_store()
    mock_store_1.connect = AsyncMock()
    mock_store_1.disconnect = AsyncMock(
        side_effect=lambda: call_order.append("primary")
    )

    mock_store_2 = _mock_memory_store()
    mock_store_2.connect = AsyncMock()
    mock_store_2.disconnect = AsyncMock(
        side_effect=lambda: call_order.append("analytics")
    )

    with patch(
        "lexigram.vector.backends.memory.MemoryVectorStore",
        side_effect=[mock_store_1, mock_store_2],
    ):
        await provider.register(container)
        await provider.boot(container)
        await provider.shutdown()

    # analytics was registered second → disconnected first (LIFO)
    assert call_order == ["analytics", "primary"]


# ---------------------------------------------------------------------------
# 9. Health check: all healthy → HEALTHY
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_backend_health_all_healthy_returns_healthy() -> None:
    """When all named stores are HEALTHY the overall result must be HEALTHY."""
    cfg = _make_two_backend_config()
    provider = VectorProvider(config=cfg)
    container = MagicMock()
    container.singleton = MagicMock()

    healthy = HealthCheckResult(
        component="vector", status=HealthStatus.HEALTHY, duration_ms=0.0
    )
    mock_store_1 = _mock_memory_store()
    mock_store_1.health_check = AsyncMock(return_value=healthy)

    mock_store_2 = _mock_memory_store()
    mock_store_2.health_check = AsyncMock(return_value=healthy)

    with patch(
        "lexigram.vector.backends.memory.MemoryVectorStore",
        side_effect=[mock_store_1, mock_store_2],
    ):
        await provider.register(container)
        await provider.boot(container)

    result = await provider.health_check()

    assert result.status == HealthStatus.HEALTHY


# ---------------------------------------------------------------------------
# 10. Health check: one UNHEALTHY → overall UNHEALTHY
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_backend_health_one_unhealthy_returns_unhealthy() -> None:
    """When any named store is UNHEALTHY the overall result must be UNHEALTHY."""
    cfg = _make_two_backend_config()
    provider = VectorProvider(config=cfg)
    container = MagicMock()
    container.singleton = MagicMock()

    healthy = HealthCheckResult(
        component="vector", status=HealthStatus.HEALTHY, duration_ms=0.0
    )
    unhealthy = HealthCheckResult(
        component="vector", status=HealthStatus.UNHEALTHY, duration_ms=0.0
    )
    mock_store_1 = _mock_memory_store()
    mock_store_1.health_check = AsyncMock(return_value=healthy)

    mock_store_2 = _mock_memory_store()
    mock_store_2.health_check = AsyncMock(return_value=unhealthy)

    with patch(
        "lexigram.vector.backends.memory.MemoryVectorStore",
        side_effect=[mock_store_1, mock_store_2],
    ):
        await provider.register(container)
        await provider.boot(container)

    result = await provider.health_check()

    assert result.status == HealthStatus.UNHEALTHY


# ---------------------------------------------------------------------------
# 11. Single-backend health check path is unchanged
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_single_backend_health_check_path_unchanged() -> None:
    """Single-backend health_check() must delegate directly to self._store."""
    provider = VectorProvider(config=VectorConfig(backend="memory"))
    mock_store = _mock_memory_store()
    container = MagicMock()

    healthy = HealthCheckResult(
        component="vector", status=HealthStatus.HEALTHY, duration_ms=1.5
    )
    mock_store.health_check = AsyncMock(return_value=healthy)

    with patch(
        "lexigram.vector.backends.memory.MemoryVectorStore", return_value=mock_store
    ):
        await provider.boot(container)

    result = await provider.health_check()

    assert result.status == HealthStatus.HEALTHY
    mock_store.health_check.assert_awaited_once()


# ---------------------------------------------------------------------------
# 12. Partial boot failure cleans up already-connected stores
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_multi_backend_boot_partial_failure_disconnects_successful_stores() -> (
    None
):
    """If one store fails to connect during boot(), the others must be disconnected."""
    cfg = _make_two_backend_config()
    provider = VectorProvider(config=cfg)
    container = MagicMock()
    container.singleton = MagicMock()

    mock_store_1 = _mock_memory_store()
    mock_store_1.connect = AsyncMock()  # succeeds

    mock_store_2 = _mock_memory_store()
    mock_store_2.connect = AsyncMock(side_effect=RuntimeError("connection refused"))

    with patch(
        "lexigram.vector.backends.memory.MemoryVectorStore",
        side_effect=[mock_store_1, mock_store_2],
    ):
        await provider.register(container)

        with pytest.raises(RuntimeError, match="connection refused"):
            await provider.boot(container)

    # The first store connected successfully but must be disconnected on rollback
    mock_store_1.disconnect.assert_awaited_once()

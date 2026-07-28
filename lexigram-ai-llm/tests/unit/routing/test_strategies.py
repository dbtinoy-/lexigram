"""Unit tests for routing strategies: Sequential, Parallel Race, Cost-Optimized,
Latency-Optimized (P5.1 - P5.4)."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.llm.routing.backends.memory import InMemoryQuotaBackend
from lexigram.ai.llm.routing.config import (
    GenerationDefaults,
    LLMConfig,
    ProviderConfig,
)
from lexigram.ai.llm.routing.strategies import (
    CostOptimizedStrategy,
    LatencyOptimizedStrategy,
    ParallelRaceStrategy,
    SequentialCascadeStrategy,
)
from lexigram.ai.llm.types import AIError, Completion, TokenUsage
from lexigram.result import Err, Ok


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_completion(text: str = "ok", model: str = "m", tokens: int = 10) -> Completion:
    return Completion(
        content=text,
        model=model,
        usage=TokenUsage(
            prompt_tokens=tokens // 2,
            completion_tokens=tokens // 2,
            total_tokens=tokens,
        ),
    )


def _make_config(
    providers: list[ProviderConfig],
) -> LLMConfig:
    return LLMConfig(
        providers=providers,
        defaults=GenerationDefaults(temperature=0.2, max_tokens=None),
    )


def _make_provider_cfg(
    name: str,
    primary: str = "model-a",
    enabled: bool = True,
) -> ProviderConfig:
    return ProviderConfig(
        name=name,
        model=primary,
        api_key="fake-key",
        enabled=enabled,
    )


def _make_client(
    *,
    text: str = "ok",
    error: Exception | None = None,
) -> MagicMock:
    """Return a mock LLM client."""
    client = MagicMock()
    if error is not None:
        client.complete = AsyncMock(return_value=Err(error))
    else:
        client.complete = AsyncMock(return_value=Ok(_make_completion(text=text)))
    return client


def _quota() -> InMemoryQuotaBackend:
    return InMemoryQuotaBackend()


MESSAGES = [{"role": "user", "content": "hello"}]


# ──────────────────────────────────────────────────────────────────────────────
# SequentialCascadeStrategy
# ──────────────────────────────────────────────────────────────────────────────


class TestSequentialCascadeStrategy:
    """Tests for SequentialCascadeStrategy.execute()."""

    @pytest.mark.asyncio
    async def test_returns_first_provider_result_on_success(self) -> None:
        """Returns the result from the first provider when it succeeds."""
        client = _make_client(text="from-groq")
        providers = [_make_provider_cfg("groq")]
        clients = {"groq:model-a": client}
        config = _make_config(providers)
        quota = _quota()

        strategy = SequentialCascadeStrategy()
        result, tried, attempts = await strategy.execute(
            providers=providers,
            clients=clients,
            quota=quota,
            config=config,
            messages=MESSAGES,
            kwargs={},
        )

        assert result is not None
        assert result.provider == "groq"
        assert result.content == "from-groq"
        assert "groq" in tried
        assert attempts == 1

    @pytest.mark.asyncio
    async def test_falls_through_to_second_provider_on_failure(self) -> None:
        """Falls through to the next provider when the first fails."""
        failing = _make_client(error=AIError("quota"))
        working = _make_client(text="from-gemini")
        providers = [
            _make_provider_cfg("groq"),
            _make_provider_cfg("gemini"),
        ]
        clients = {"groq:model-a": failing, "gemini:model-a": working}
        config = _make_config(providers)
        quota = _quota()

        strategy = SequentialCascadeStrategy()
        result, tried, attempts = await strategy.execute(
            providers=providers,
            clients=clients,
            quota=quota,
            config=config,
            messages=MESSAGES,
            kwargs={},
        )

        assert result is not None
        assert result.provider == "gemini"

    @pytest.mark.asyncio
    async def test_skips_exhausted_provider(self) -> None:
        """Skips providers already marked as exhausted in the quota backend."""
        groq = _make_client(text="groq-would-succeed")
        gemini = _make_client(text="from-gemini")
        providers = [
            _make_provider_cfg("groq"),
            _make_provider_cfg("gemini"),
        ]
        clients = {"groq:model-a": groq, "gemini:model-a": gemini}
        quota = _quota()
        await quota.mark_exhausted("groq:model-a")
        config = _make_config(providers)

        strategy = SequentialCascadeStrategy()
        result, tried, attempts = await strategy.execute(
            providers=providers,
            clients=clients,
            quota=quota,
            config=config,
            messages=MESSAGES,
            kwargs={},
        )

        assert result is not None
        assert result.provider == "gemini"
        groq.complete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_none_when_all_providers_fail(self) -> None:
        """Returns None when every provider raises an error."""
        error = AIError("down")
        providers = [
            _make_provider_cfg("p1"),
            _make_provider_cfg("p2"),
        ]
        clients = {"p1:model-a": _make_client(error=error), "p2:model-a": _make_client(error=error)}
        config = _make_config(providers)
        quota = _quota()

        strategy = SequentialCascadeStrategy()
        result, tried, attempts = await strategy.execute(
            providers=providers,
            clients=clients,
            quota=quota,
            config=config,
            messages=MESSAGES,
            kwargs={},
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_skips_disabled_provider(self) -> None:
        """Disabled providers are never attempted."""
        disabled = _make_client(text="should-not-appear")
        enabled = _make_client(text="enabled")
        providers = [
            _make_provider_cfg("disabled-p", enabled=False),
            _make_provider_cfg("enabled-p"),
        ]
        clients = {"disabled-p:model-a": disabled, "enabled-p:model-a": enabled}
        config = _make_config(providers)
        quota = _quota()

        strategy = SequentialCascadeStrategy()
        result, _, _ = await strategy.execute(
            providers=providers,
            clients=clients,
            quota=quota,
            config=config,
            messages=MESSAGES,
            kwargs={},
        )

        assert result is not None
        assert result.provider == "enabled-p"
        disabled.complete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_model_failure_exhausts_provider(self) -> None:
        """When the model fails, the provider is not retried (no fallback in new design)."""
        attempts_args: list[dict] = []

        async def _complete(messages, **kwargs):
            model = kwargs.get("model", "unknown")
            attempts_args.append({"model": model})
            return Err(AIError("model down"))

        client = MagicMock()
        client.complete = AsyncMock(side_effect=_complete)

        providers = [
            _make_provider_cfg("groq", primary="primary-model")
        ]
        clients = {"groq:primary-model": client}
        config = _make_config(providers)
        quota = _quota()

        strategy = SequentialCascadeStrategy()
        result, _, attempts = await strategy.execute(
            providers=providers,
            clients=clients,
            quota=quota,
            config=config,
            messages=MESSAGES,
            kwargs={},
        )

        assert result is None
        assert attempts == 1


# ──────────────────────────────────────────────────────────────────────────────
# ParallelRaceStrategy
# ──────────────────────────────────────────────────────────────────────────────


class TestParallelRaceStrategy:
    """Tests for ParallelRaceStrategy.execute() (P5.1)."""

    @pytest.mark.asyncio
    async def test_returns_first_completing_provider(self) -> None:
        """Returns a result with provider set correctly."""
        p1 = _make_client(text="provider1")
        p2 = _make_client(text="provider2")
        providers = [_make_provider_cfg("p1"), _make_provider_cfg("p2")]
        clients = {"p1:model-a": p1, "p2:model-a": p2}
        config = _make_config(providers)
        quota = _quota()

        strategy = ParallelRaceStrategy()
        result, tried, total = await strategy.execute(
            providers=providers,
            clients=clients,
            quota=quota,
            config=config,
            messages=MESSAGES,
            kwargs={},
        )

        assert result is not None
        # Race: exactly one provider wins
        assert result.provider in ("p1", "p2")
        assert len(tried) == 2  # both listed as tried
        assert total == 2       # both were launched

    @pytest.mark.asyncio
    async def test_returns_none_when_all_providers_fail(self) -> None:
        """Returns None when every parallel attempt fails."""
        error = AIError("down")
        providers = [_make_provider_cfg("p1"), _make_provider_cfg("p2")]
        clients = {
            "p1:model-a": _make_client(error=error),
            "p2:model-a": _make_client(error=error),
        }
        config = _make_config(providers)
        quota = _quota()

        strategy = ParallelRaceStrategy()
        result, _, _ = await strategy.execute(
            providers=providers,
            clients=clients,
            quota=quota,
            config=config,
            messages=MESSAGES,
            kwargs={},
        )

        assert result is None

    @pytest.mark.asyncio
    async def test_skips_exhausted_providers(self) -> None:
        """Exhausted providers are not launched at all."""
        p1 = _make_client(text="p1")
        p2 = _make_client(text="p2")
        providers = [_make_provider_cfg("p1"), _make_provider_cfg("p2")]
        clients = {"p1:model-a": p1, "p2:model-a": p2}
        quota = _quota()
        await quota.mark_exhausted("p1:model-a")
        config = _make_config(providers)

        strategy = ParallelRaceStrategy()
        result, _, total = await strategy.execute(
            providers=providers,
            clients=clients,
            quota=quota,
            config=config,
            messages=MESSAGES,
            kwargs={},
        )

        assert result is not None
        assert result.provider == "p2"
        # Only p2 was launched
        assert total == 1
        p1.complete.assert_not_awaited()

    @pytest.mark.asyncio
    async def test_returns_none_when_no_eligible_providers(self) -> None:
        """Returns None immediately when all providers are exhausted."""
        quota = _quota()
        providers = [_make_provider_cfg("p1")]
        clients = {"p1:model-a": _make_client()}
        await quota.mark_exhausted("p1:model-a")
        config = _make_config(providers)

        strategy = ParallelRaceStrategy()
        result, _, total = await strategy.execute(
            providers=providers,
            clients=clients,
            quota=quota,
            config=config,
            messages=MESSAGES,
            kwargs={},
        )

        assert result is None
        assert total == 0


# ──────────────────────────────────────────────────────────────────────────────
# CostOptimizedStrategy
# ──────────────────────────────────────────────────────────────────────────────


class TestCostOptimizedStrategy:
    """Tests for CostOptimizedStrategy.execute() (P5.2)."""

    def _make_pricing_manager(self, costs: dict[str, tuple[float, float]]) -> MagicMock:
        """Create a mock PricingManager with given model → (prompt_rate, completion_rate)."""
        pm = MagicMock()

        async def _get_pricing(model: str):
            if model in costs:
                p, c = costs[model]
                pricing = MagicMock()
                pricing.prompt_per_1m = p
                pricing.completion_per_1m = c
                return pricing
            raise KeyError(model)

        pm.get_pricing = _get_pricing
        return pm

    @pytest.mark.asyncio
    async def test_tries_cheapest_provider_first(self) -> None:
        """Cheapest provider (by token cost) is attempted before expensive one."""
        call_order: list[str] = []

        async def _complete_cheap(messages, **kwargs):
            call_order.append("cheap")
            return Ok(_make_completion(text="cheap-result"))

        async def _complete_expensive(messages, **kwargs):
            call_order.append("expensive")
            return Ok(_make_completion(text="expensive-result"))

        cheap_client = MagicMock()
        cheap_client.complete = AsyncMock(side_effect=_complete_cheap)
        expensive_client = MagicMock()
        expensive_client.complete = AsyncMock(side_effect=_complete_expensive)

        providers = [
            _make_provider_cfg("expensive", primary="expensive-model"),
            _make_provider_cfg("cheap", primary="cheap-model"),
        ]
        clients = {"expensive:expensive-model": expensive_client, "cheap:cheap-model": cheap_client}
        # cheap-model costs $1/1M prompt + $2/1M completion
        # expensive-model costs $10/1M prompt + $20/1M completion
        pm = self._make_pricing_manager(
            {
                "cheap-model": (1.0, 2.0),
                "expensive-model": (10.0, 20.0),
            }
        )
        config = _make_config(providers)
        quota = _quota()

        strategy = CostOptimizedStrategy(pricing_manager=pm)
        result, _, _ = await strategy.execute(
            providers=providers,
            clients=clients,
            quota=quota,
            config=config,
            messages=MESSAGES,
            kwargs={},
        )

        assert result is not None
        assert result.content == "cheap-result"
        assert call_order[0] == "cheap"

    @pytest.mark.asyncio
    async def test_unknown_cost_provider_tried_last(self) -> None:
        """Providers without pricing data are sorted last (cost=infinity)."""
        call_order: list[str] = []

        async def _complete_known(messages, **kwargs):
            call_order.append("known")
            return Ok(_make_completion(text="known"))

        async def _complete_unknown(messages, **kwargs):
            call_order.append("unknown")
            return Ok(_make_completion(text="unknown"))

        known_client = MagicMock()
        known_client.complete = AsyncMock(side_effect=_complete_known)
        unknown_client = MagicMock()
        unknown_client.complete = AsyncMock(side_effect=_complete_unknown)

        providers = [
            _make_provider_cfg("unknown-pricing", primary="no-pricing-model"),
            _make_provider_cfg("known-pricing", primary="known-model"),
        ]
        clients = {
            "unknown-pricing:no-pricing-model": unknown_client,
            "known-pricing:known-model": known_client,
        }
        pm = self._make_pricing_manager({"known-model": (1.0, 1.0)})
        config = _make_config(providers)
        quota = _quota()

        strategy = CostOptimizedStrategy(pricing_manager=pm)
        result, _, _ = await strategy.execute(
            providers=providers,
            clients=clients,
            quota=quota,
            config=config,
            messages=MESSAGES,
            kwargs={},
        )

        assert result is not None
        assert call_order[0] == "known"

    @pytest.mark.asyncio
    async def test_falls_through_to_next_on_failure(self) -> None:
        """Falls through to next-cheapest provider when cheapest fails."""
        cheap_client = _make_client(error=AIError("cheap down"))
        expensive_client = _make_client(text="expensive-result")

        providers = [
            _make_provider_cfg("cheap", primary="cheap-model"),
            _make_provider_cfg("expensive", primary="expensive-model"),
        ]
        clients = {"cheap:cheap-model": cheap_client, "expensive:expensive-model": expensive_client}
        pm = self._make_pricing_manager(
            {"cheap-model": (1.0, 1.0), "expensive-model": (5.0, 5.0)}
        )
        config = _make_config(providers)
        quota = _quota()

        strategy = CostOptimizedStrategy(pricing_manager=pm)
        result, _, _ = await strategy.execute(
            providers=providers,
            clients=clients,
            quota=quota,
            config=config,
            messages=MESSAGES,
            kwargs={},
        )

        assert result is not None
        assert result.content == "expensive-result"


# ──────────────────────────────────────────────────────────────────────────────
# LatencyOptimizedStrategy
# ──────────────────────────────────────────────────────────────────────────────


class TestLatencyOptimizedStrategy:
    """Tests for LatencyOptimizedStrategy.execute() (P5.4)."""

    @pytest.mark.asyncio
    async def test_unknown_latency_providers_tried_first(self) -> None:
        """Providers with no latency history are tried before those with recorded history."""
        call_order: list[str] = []

        async def _a(messages, **kwargs):
            call_order.append("a")
            return Ok(_make_completion(text="a"))

        async def _b(messages, **kwargs):
            call_order.append("b")
            return Ok(_make_completion(text="b"))

        client_a = MagicMock()
        client_a.complete = AsyncMock(side_effect=_a)
        client_b = MagicMock()
        client_b.complete = AsyncMock(side_effect=_b)

        providers = [
            _make_provider_cfg("known-latency"),
            _make_provider_cfg("unknown-latency"),
        ]
        clients = {"known-latency:model-a": client_a, "unknown-latency:model-a": client_b}
        config = _make_config(providers)
        quota = _quota()

        strategy = LatencyOptimizedStrategy(skip_unhealthy=False)
        # Record latency only for provider "known-latency"
        strategy.record_latency("known-latency:model-a", 500.0)

        result, _, _ = await strategy.execute(
            providers=providers,
            clients=clients,
            quota=quota,
            config=config,
            messages=MESSAGES,
            kwargs={},
        )

        assert result is not None
        # unknown-latency should have been tried first (exploration)
        assert call_order[0] == "b"

    @pytest.mark.asyncio
    async def test_lower_latency_provider_tried_first(self) -> None:
        """Provider with lower average latency is tried before higher-latency one."""
        call_order: list[str] = []

        async def _fast(messages, **kwargs):
            call_order.append("fast")
            return Ok(_make_completion(text="fast"))

        async def _slow(messages, **kwargs):
            call_order.append("slow")
            return Ok(_make_completion(text="slow"))

        fast_client = MagicMock()
        fast_client.complete = AsyncMock(side_effect=_fast)
        slow_client = MagicMock()
        slow_client.complete = AsyncMock(side_effect=_slow)

        providers = [
            _make_provider_cfg("slow-p"),
            _make_provider_cfg("fast-p"),
        ]
        clients = {"slow-p:model-a": slow_client, "fast-p:model-a": fast_client}
        config = _make_config(providers)
        quota = _quota()

        strategy = LatencyOptimizedStrategy(skip_unhealthy=False)
        strategy.record_latency("slow-p:model-a", 800.0)
        strategy.record_latency("fast-p:model-a", 100.0)

        result, _, _ = await strategy.execute(
            providers=providers,
            clients=clients,
            quota=quota,
            config=config,
            messages=MESSAGES,
            kwargs={},
        )

        assert result is not None
        assert call_order[0] == "fast"

    @pytest.mark.asyncio
    async def test_skip_unhealthy_bypasses_unhealthy_provider(self) -> None:
        """Providers reporting UNHEALTHY are skipped when skip_unhealthy=True."""
        unhealthy_client = MagicMock()
        health_result = MagicMock()
        health_result.status = "unhealthy"
        unhealthy_client.health_check = AsyncMock(return_value=health_result)
        unhealthy_client.complete = AsyncMock(return_value=Ok(_make_completion(text="x")))

        healthy_client = MagicMock()

        async def _hc_ok(**kwargs):
            r = MagicMock()
            r.status = "healthy"
            return r

        healthy_client.health_check = AsyncMock(side_effect=_hc_ok)
        healthy_client.complete = AsyncMock(return_value=Ok(_make_completion(text="healthy-ok")))

        providers = [
            _make_provider_cfg("unhealthy-p"),
            _make_provider_cfg("healthy-p"),
        ]
        clients = {"unhealthy-p:model-a": unhealthy_client, "healthy-p:model-a": healthy_client}
        config = _make_config(providers)
        quota = _quota()

        strategy = LatencyOptimizedStrategy(skip_unhealthy=True, health_timeout=1.0)
        result, tried, _ = await strategy.execute(
            providers=providers,
            clients=clients,
            quota=quota,
            config=config,
            messages=MESSAGES,
            kwargs={},
        )

        assert result is not None
        assert result.content == "healthy-ok"
        unhealthy_client.complete.assert_not_awaited()

    def test_record_latency_tracks_rolling_window(self) -> None:
        """record_latency() maintains a rolling window of samples."""
        strategy = LatencyOptimizedStrategy(window_size=3)
        strategy.record_latency("p", 100.0)
        strategy.record_latency("p", 200.0)
        strategy.record_latency("p", 300.0)
        # 4th evicts 1st (deque maxlen=3)
        strategy.record_latency("p", 400.0)

        avg = strategy._avg_latency("p")
        assert avg == pytest.approx((200.0 + 300.0 + 400.0) / 3)

    def test_avg_latency_returns_minus_one_for_unknown_provider(self) -> None:
        """_avg_latency() returns -1.0 for providers with no samples yet."""
        strategy = LatencyOptimizedStrategy()
        assert strategy._avg_latency("new-provider") == -1.0

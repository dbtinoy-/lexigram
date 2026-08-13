import pytest

from lexigram.resilience.pipeline.executor import ResiliencePipeline


class DummyStep:
    def __init__(self, name: str, log: list[str]):
        self.name = name
        self.log = log

    async def call(self, func):
        # simulate bulkhead/circuit
        self.log.append(self.name)
        return await func()

    async def execute(self, func):
        # simulate retry
        self.log.append(self.name)
        return await func()


class DummyTimeoutContext:
    def __init__(self, cfg, log: list[str]):
        self.log = log

    async def __aenter__(self):
        self.log.append("timeout-enter")

    async def __aexit__(self, exc_type, exc, tb):
        self.log.append("timeout-exit")


@pytest.mark.asyncio
async def test_resilience_pipeline_default_order(monkeypatch):
    # validate that default order is bulkhead -> circuit_breaker -> retry -> timeout
    log: list[str] = []

    # patch timeout_context to use our dummy
    monkeypatch.setattr(
        "lexigram.resilience.pipeline.executor.timeout_context",
        lambda cfg: DummyTimeoutContext(cfg, log),
    )

    # create empty pipeline and then inject dummy steps
    pipeline = ResiliencePipeline()
    pipeline.bulkhead = DummyStep("bulkhead", log)
    pipeline.circuit_breaker = DummyStep("circuit_breaker", log)
    pipeline.retry_policy = DummyStep("retry", log)
    pipeline.timeout_config = object()  # truthy to trigger wrapper

    async def work():
        log.append("func")
        return "ok"

    result = await pipeline.execute(work)
    assert result == "ok"

    # the log should show wrappers in the order declared by default
    assert log == [
        "bulkhead",
        "circuit_breaker",
        "retry",
        "timeout-enter",
        "func",
        "timeout-exit",
    ]


@pytest.mark.asyncio
async def test_resilience_pipeline_custom_order(monkeypatch):
    # custom sequence: retry outermost, then timeout, then bulkhead, then circuit
    log: list[str] = []

    monkeypatch.setattr(
        "lexigram.resilience.pipeline.executor.timeout_context",
        lambda cfg: DummyTimeoutContext(cfg, log),
    )

    pipeline = ResiliencePipeline(order=["retry", "timeout", "bulkhead", "circuit_breaker"])
    pipeline.bulkhead = DummyStep("bulkhead", log)
    pipeline.circuit_breaker = DummyStep("circuit_breaker", log)
    pipeline.retry_policy = DummyStep("retry", log)
    pipeline.timeout_config = object()

    async def work():
        log.append("func")
        return 42

    result = await pipeline.execute(work)
    assert result == 42

    # with the chosen order the outermost should be retry, then timeout, etc.
    assert log == [
        "retry",
        "timeout-enter",
        "bulkhead",
        "circuit_breaker",
        "func",
        "timeout-exit",
    ]


@pytest.mark.asyncio
async def test_resilience_pipeline_invalid_order():
    with pytest.raises(ValueError):
        ResiliencePipeline(order=["foo", "bulkhead"])

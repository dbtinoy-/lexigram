
from lexigram.monitor.config import MonitorConfig
from lexigram.monitor.health import HealthCheckRegistry
from lexigram.monitor.di.factories import create_provider_from_config


class DummyContainer:
    def __init__(self):
        self.mapping = {}

    def singleton(self, key, factory):
        value = factory() if callable(factory) else factory
        self.mapping[key] = value

    async def resolve(self, cls):
        if cls in self.mapping:
            return self.mapping[cls]
        raise RuntimeError("Not registered")

    def has(self, cls):
        return cls in self.mapping


class DummyExporter:
    def __init__(self):
        self.exported = []

    def export(self, spans):
        self.exported.append(list(spans))


def test_provider_tracer_respects_max_spans_config():
    # Small cap to trigger auto-flush
    cfg = MonitorConfig(tracing={"max_spans": 3, "service_name": "svc"})

    provider = create_provider_from_config(cfg)

    # Replace exporter with a test double
    exporter = DummyExporter()
    provider.tracer.exporter = exporter

    # Create spans exceeding the max_spans threshold
    for i in range(4):
        provider.tracer.start_span(f"s{i}")

    assert len(exporter.exported) >= 1


import pytest

@pytest.mark.asyncio
async def test_register_provides_health_check_registry():
    cfg = MonitorConfig()
    provider = create_provider_from_config(cfg)

    container = DummyContainer()
    # Ensure initial absence
    assert not container.has(HealthCheckRegistry)

    await provider.register(container)

    assert container.has(HealthCheckRegistry)
    assert isinstance(container.mapping[HealthCheckRegistry], HealthCheckRegistry)


@pytest.mark.asyncio
async def test_tracer_registered_in_di_and_no_global_helpers():
    """Ensure Tracer is registered via DI and no global helpers remain."""
    cfg = MonitorConfig(tracing={"max_spans": 3, "service_name": "svc-di"})
    provider = create_provider_from_config(cfg)

    container = DummyContainer()
    await provider.register(container)

    # Tracer should be registered in the container
    from lexigram.monitor.tracing import Tracer

    assert container.has(Tracer)
    tracer = await container.resolve(Tracer)
    assert tracer.service_name == "svc-di"

    # Replace exporter to observe auto-flush behavior
    exporter = DummyExporter()
    tracer.exporter = exporter
    for i in range(4):
        tracer.start_span(f"s{i}")
    assert len(exporter.exported) >= 1

    # Ensure no module-level global helpers are present
    import importlib

    tracing_mod = importlib.import_module("lexigram.monitor.tracing")
    assert not hasattr(tracing_mod, "get_tracer")
    assert not hasattr(tracing_mod, "set_tracer")

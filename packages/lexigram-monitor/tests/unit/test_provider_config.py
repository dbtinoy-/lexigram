
import pytest

from lexigram.monitor.config import MonitorConfig
from lexigram.monitor.di.factories import create_provider_from_config

try:
    from opentelemetry.sdk.trace import TracerProvider as _OtelTracerProvider  # noqa: F401

    HAS_OPENTELEMETRY = True
except ImportError:
    HAS_OPENTELEMETRY = False


def test_create_provider_from_dict_prometheus():
    pytest.importorskip("prometheus_client", reason="Prometheus backend requires prometheus_client")
    cfg = {"backend_type": "prometheus", "prometheus": {"port": 8555}}
    provider = create_provider_from_config(cfg)
    assert type(provider.backend).__name__ == "PrometheusBackend"


@pytest.mark.skipif(not HAS_OPENTELEMETRY, reason="opentelemetry not installed")
def test_create_provider_from_model_opentelemetry():
    m = MonitorConfig(
        backend_type="opentelemetry",
        opentelemetry={"service_name": "svc", "endpoint": "http://example"},
    )
    provider = create_provider_from_config(m)
    assert type(provider.backend).__name__ == "OpenTelemetryBackend"

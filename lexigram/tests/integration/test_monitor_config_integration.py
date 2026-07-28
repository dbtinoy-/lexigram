"""Tests that LexigramConfig accepts monitor configuration when monitor package is available."""

import pytest

from lexigram.config import LexigramConfig

try:
    from lexigram.monitor.config import BackendType, MonitorProviderConfig

    HAS_MONITOR = True
except ImportError:
    HAS_MONITOR = False


@pytest.mark.integration
@pytest.mark.skipif(not HAS_MONITOR, reason="monitor package not available")
def test_lexigram_config_accepts_monitor():
    cfg = LexigramConfig(
        monitor=MonitorProviderConfig(backend_type=BackendType.PROMETHEUS),
    )
    assert cfg.monitor is not None
    assert cfg.monitor.backend_type == BackendType.PROMETHEUS

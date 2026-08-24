"""Tests for the demo hub registry and API surface."""

from __future__ import annotations

import pytest

registry_mod = pytest.importorskip("demo_hub.services.registry")


def test_registry_lists_all_thirteen_live_services() -> None:
    registry = registry_mod.ServiceRegistry()
    services = registry.services
    assert len([s for s in services if s.kind == "web"]) == 13


def test_registry_ports_are_unique_and_known() -> None:
    registry = registry_mod.ServiceRegistry()
    ports = [s.port for s in registry.services]
    assert len(set(ports)) == len(ports)
    assert 7000 not in ports  # hub never checks itself


def test_registry_includes_llm_reproducibility_as_cli() -> None:
    registry = registry_mod.ServiceRegistry()
    cli_services = [s for s in registry.services if s.kind == "cli"]
    assert len(cli_services) == 1
    assert cli_services[0].slug == "llm-reproducibility"

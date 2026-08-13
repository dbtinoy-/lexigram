"""Tests for the gateway served-model catalog.

Covers the OpenAI/Anthropic/Gemini list payloads, the OpenAI/Gemini
detail payloads, and the drained/disabled channel filtering rules.
"""

from __future__ import annotations

from lexigram.ai.relay.gateway.catalog import ModelCatalogService
from lexigram.ai.relay.gateway.channels import RelayChannelRegistry
from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.contracts.ai.relay import RelayChannel, RelayFormat


def config() -> RelayGatewayConfig:
    """Gateway config with two channels serving overlapping models."""
    return RelayGatewayConfig(
        channels=(
            RelayChannel(
                name="claude",
                upstream_base_url="https://upstream.example.com/claude",
                target_format=RelayFormat.CLAUDE,
                models=("claude-sonnet", "claude-haiku"),
            ),
            RelayChannel(
                name="gemini",
                upstream_base_url="https://upstream.example.com/gemini",
                target_format=RelayFormat.GEMINI,
                models=("gemini-pro", "claude-sonnet"),
            ),
        )
    )


def service() -> ModelCatalogService:
    """A catalog over the two-channel config."""
    return ModelCatalogService(RelayChannelRegistry(config()))


def test_openai_list_shape() -> None:
    payload = service().list_openai()
    assert payload["object"] == "list"
    ids = [entry["id"] for entry in payload["data"]]
    assert ids == ["claude-haiku", "claude-sonnet", "gemini-pro"]
    assert all(entry["object"] == "model" for entry in payload["data"])


def test_claude_list_shape() -> None:
    payload = service().list_claude()
    ids = [entry["id"] for entry in payload["data"]]
    assert ids == ["claude-haiku", "claude-sonnet", "gemini-pro"]
    assert all(entry["type"] == "model" for entry in payload["data"])
    assert all(entry["display_name"] == entry["id"] for entry in payload["data"])


def test_gemini_list_shape() -> None:
    payload = service().list_gemini()
    names = [entry["name"] for entry in payload["models"]]
    assert names == [
        "models/claude-haiku",
        "models/claude-sonnet",
        "models/gemini-pro",
    ]
    assert all(
        entry["supportedGenerationMethods"] == ["generateContent"]
        for entry in payload["models"]
    )


def test_openai_detail_for_served_model() -> None:
    detail = service().openai_detail("claude-sonnet")
    assert detail is not None
    assert detail["id"] == "claude-sonnet"


def test_gemini_detail_for_served_model() -> None:
    detail = service().gemini_detail("gemini-pro")
    assert detail is not None
    assert detail["name"] == "models/gemini-pro"


def test_detail_none_for_unknown_model() -> None:
    assert service().openai_detail("unknown") is None
    assert service().gemini_detail("unknown") is None


def test_model_exists() -> None:
    catalog = service()
    assert catalog.model_exists("claude-haiku")
    assert not catalog.model_exists("unknown")


def test_drained_channel_models_hidden() -> None:
    registry = RelayChannelRegistry(config())
    registry.set_runtime_enabled("claude", False)
    catalog = ModelCatalogService(registry)
    payload = catalog.list_openai()
    ids = [entry["id"] for entry in payload["data"]]
    assert ids == ["claude-sonnet", "gemini-pro"]
    assert catalog.model_exists("gemini-pro")
    assert not catalog.model_exists("claude-haiku")


def test_config_disabled_channel_models_hidden() -> None:
    cfg = RelayGatewayConfig(
        channels=(
            RelayChannel(
                name="claude",
                upstream_base_url="https://upstream.example.com/claude",
                target_format=RelayFormat.CLAUDE,
                models=("claude-sonnet",),
                enabled=False,
            ),
        )
    )
    catalog = ModelCatalogService(RelayChannelRegistry(cfg))
    assert catalog.list_openai()["data"] == []
    assert not catalog.model_exists("claude-sonnet")

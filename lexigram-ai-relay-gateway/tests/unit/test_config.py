"""Tests for the gateway config loader.

Covers ``RelayGatewayConfig.from_mapping`` channel coercion, top-level
field mapping, unknown-key rejection, and the failover defaults.
"""

from __future__ import annotations

import pytest

from lexigram.ai.relay.gateway.config import RelayGatewayConfig
from lexigram.contracts.ai.relay import RelayFormat


def full_mapping() -> dict[str, object]:
    """A mapping with every supported top-level key."""
    return {
        "channels": [
            {
                "name": "claude",
                "upstream_base_url": "https://up.example/claude",
                "target_format": "CLAUDE",
                "models": ["claude-sonnet", "alias"],
                "capabilities": ["vision"],
                "priority": 10,
                "weight": 200,
                "enabled": True,
                "timeout_seconds": 30.0,
                "model_map": {"alias": "claude-sonnet"},
            },
            {
                "name": "gemini",
                "upstream_base_url": "https://up.example/gemini",
                "target_format": "GEMINI",
                "models": ["gemini-pro"],
                "endpoint_kinds": ["video"],
            },
        ],
        "model_suffix": {"claude": ":thinking"},
        "provider_options": {"claude": {"thinking": True}},
        "auto_test_channels": True,
        "auto_test_interval_seconds": 30,
        "max_upstream_retries": 2,
        "load_balancing": "weighted",
        "job_ttl_seconds": 120,
        "require_auth": True,
        "rate_limits": {"*": {"max": 10, "window_seconds": 60}},
        "auto_disable_on_failures": True,
        "failover_failure_threshold": 5,
    }


def test_full_mapping_round_trip() -> None:
    cfg = RelayGatewayConfig.from_mapping(full_mapping())
    assert len(cfg.channels) == 2
    claude, gemini = cfg.channels
    assert claude.name == "claude"
    assert claude.target_format is RelayFormat.CLAUDE
    assert claude.model_map == {"alias": "claude-sonnet"}
    assert claude.priority == 10
    assert claude.weight == 200
    assert claude.timeout_seconds == 30.0
    assert claude.capabilities == frozenset({"vision"})
    assert gemini.target_format is RelayFormat.GEMINI
    assert gemini.endpoint_kinds == frozenset({"video"})
    assert cfg.model_suffix == {"claude": ":thinking"}
    assert cfg.max_upstream_retries == 2
    assert cfg.load_balancing == "weighted"
    assert cfg.auto_disable_on_failures is True
    assert cfg.failover_failure_threshold == 5
    assert cfg.require_auth is True


def test_minimal_mapping_defaults() -> None:
    cfg = RelayGatewayConfig.from_mapping(
        {
            "channels": [
                {
                    "name": "a",
                    "upstream_base_url": "https://up.example",
                    "target_format": "OPENAI_CHAT",
                    "models": ["m"],
                }
            ]
        }
    )
    assert cfg.auto_disable_on_failures is False
    assert cfg.failover_failure_threshold == 3
    assert cfg.load_balancing == "deterministic"
    assert cfg.max_upstream_retries == 0
    assert cfg.require_auth is True


def test_require_auth_defaults_to_true() -> None:
    cfg = RelayGatewayConfig()
    assert cfg.require_auth is True
    assert RelayGatewayConfig.from_mapping({}).require_auth is True


def test_require_auth_explicit_false_opt_out() -> None:
    cfg = RelayGatewayConfig.from_mapping({"require_auth": False})
    assert cfg.require_auth is False


def test_empty_channels_defaults() -> None:
    cfg = RelayGatewayConfig.from_mapping({})
    assert cfg.channels == ()


def test_unknown_top_level_key_rejected() -> None:
    with pytest.raises(ValueError, match="unknown gateway config keys"):
        RelayGatewayConfig.from_mapping({"channels": [], "billing_url": "x"})


def test_unknown_channel_key_rejected() -> None:
    with pytest.raises(ValueError, match="channels\\[0\\] has unknown keys"):
        RelayGatewayConfig.from_mapping({"channels": [{"name": "a", "surprise": True}]})


def test_channels_must_be_a_list() -> None:
    with pytest.raises(TypeError, match="channels must be a list"):
        RelayGatewayConfig.from_mapping({"channels": {"a": {}}})


def test_channel_missing_required_keys_rejected() -> None:
    with pytest.raises(ValueError, match="missing keys"):
        RelayGatewayConfig.from_mapping({"channels": [{"name": "a"}]})


def test_unknown_target_format_rejected() -> None:
    with pytest.raises(ValueError, match="unknown target_format"):
        RelayGatewayConfig.from_mapping(
            {
                "channels": [
                    {
                        "name": "a",
                        "upstream_base_url": "https://up.example",
                        "target_format": "SOAP",
                        "models": ["m"],
                    }
                ]
            }
        )


def test_non_positive_failover_threshold_rejected() -> None:
    cfg = RelayGatewayConfig.from_mapping(full_mapping())
    with pytest.raises(ValueError, match="failover_failure_threshold"):
        RelayGatewayConfig(
            channels=cfg.channels,
            auto_disable_on_failures=True,
            failover_failure_threshold=0,
        )

"""Intentional environment-variable reads that are outside package config models."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class NonConfigEnvSource:
    """Static metadata for env vars intentionally read outside config.py."""

    source_file: str
    env_var: str
    rationale: str


NON_CONFIG_ENV_SOURCES: tuple[NonConfigEnvSource, ...] = (
    NonConfigEnvSource(
        source_file="core/lexigram/src/lexigram/logging/debug.py",
        env_var="LEX_DEBUG",
        rationale="Early-boot logging toggle before typed config is available.",
    ),
    NonConfigEnvSource(
        source_file="core/lexigram/src/lexigram/app/base.py",
        env_var="LEX_QUIET",
        rationale="Controls startup banner suppression during process bootstrap.",
    ),
    NonConfigEnvSource(
        source_file="experimental/apps/lexigram-cli/src/lexigram/cli/lib/config_loader.py",
        env_var="LEX_CONFIG",
        rationale="CLI override for explicit configuration file path.",
    ),
)


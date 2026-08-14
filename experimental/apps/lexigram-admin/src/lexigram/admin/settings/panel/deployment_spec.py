"""Deployment info configuration specification — read-only, env-sourced."""

from __future__ import annotations

import os

from lexigram.admin.settings.panel.nodes import ConfigSpec, StringNode
from lexigram.admin.settings.panel.registry import ConfigRegistry

__all__ = ["DeploymentInfoSpec", "register_spec"]


class DeploymentInfoSpec(ConfigSpec):
    """Read-only deployment info sourced from environment variables."""

    namespace = "admin.deployment"
    label = "Deployment Info"
    icon = "server"
    description = "Read-only environment and runtime configuration."
    store_name = "env"

    environment = StringNode(
        label="Environment",
        default=os.environ.get("ENVIRONMENT", "unknown"),
        readonly=True,
        help_text="Deployment environment name.",
    )
    log_level = StringNode(
        label="Log Level",
        default=os.environ.get("LOG_LEVEL", "INFO"),
        readonly=True,
        help_text="Configured application log level.",
    )


def register_spec(registry: ConfigRegistry) -> None:
    """Register this spec with the config registry."""
    registry.register_spec(DeploymentInfoSpec)

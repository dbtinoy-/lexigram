"""Admin resources module.

Resources define the configuration for admin UI views including
columns, actions, filters, and permissions.
"""

from __future__ import annotations

from lexigram.admin.resources.base import Resource
from lexigram.admin.resources.config import ResourceConfig, TableConfiguration
from lexigram.admin.resources.lenses import LensRegistry, ResourceLens

__all__ = [
    "LensRegistry",
    "Resource",
    "ResourceConfig",
    "ResourceLens",
    "TableConfiguration",
]

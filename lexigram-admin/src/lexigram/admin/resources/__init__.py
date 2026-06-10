"""Admin resources module.

Resources define the configuration for admin UI views including
columns, actions, filters, and permissions.
"""

from __future__ import annotations

from lexigram.admin.resources.base import Resource
from lexigram.admin.resources.config import ResourceConfig, TableConfiguration
from lexigram.admin.resources.lenses import LensRegistry, ResourceLens
from lexigram.admin.resources.mixins import HasInfolist

__all__ = [
    "HasInfolist",
    "LensRegistry",
    "Resource",
    "ResourceConfig",
    "ResourceLens",
    "TableConfiguration",
]

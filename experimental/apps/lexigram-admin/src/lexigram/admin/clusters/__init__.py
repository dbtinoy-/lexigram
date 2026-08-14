"""Clusters — first-class grouping of resources and pages."""

from __future__ import annotations

from lexigram.admin.clusters.base import Cluster
from lexigram.admin.clusters.registry import INFRASTRUCTURE_CLUSTER, ClusterRegistry

__all__ = [
    "INFRASTRUCTURE_CLUSTER",
    "Cluster",
    "ClusterRegistry",
]

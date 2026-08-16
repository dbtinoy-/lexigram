"""DI provider for the graph sub-namespace of lexigram-nosql."""

from __future__ import annotations

from lexigram.graph.di.provider import GraphProvider
from lexigram.graph.module import GraphModule

__all__ = ["GraphModule", "GraphProvider"]

"""DI container package — Container, Scope, and component facades."""

from __future__ import annotations

from lexigram.di.container.container import Container
from lexigram.di.container.registrar import ContainerRegistrarImpl
from lexigram.di.container.resolver import ContainerResolverImpl
from lexigram.di.container.scope import Scope
from lexigram.di.container.validation import ContainerValidator, OrphanedRegistration

__all__ = [
    "Container",
    "ContainerRegistrarImpl",
    "ContainerResolverImpl",
    "ContainerValidator",
    "OrphanedRegistration",
    "Scope",
]

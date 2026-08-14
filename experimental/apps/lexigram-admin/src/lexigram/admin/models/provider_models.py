from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from starlette.routing import Route


@dataclass
class Command:
    """A command palette command."""

    label: str
    href: str
    icon: str = ""
    shortcut: str = ""


@dataclass
class AdminProviderState:
    """Internal state for AdminProvider."""

    mounted: bool = False
    started: bool = False
    modules_initialized: bool = False
    resources: dict[str, Any] = field(default_factory=dict)
    deferred_resources: dict[str, type] = field(default_factory=dict)
    discovered_resource_packages: list[str] = field(default_factory=list)
    discovered_controller_packages: list[str] = field(default_factory=list)
    routes: list[Route] = field(default_factory=list)
    middleware: list[Any] = field(default_factory=list)
    commands: list[Command] = field(default_factory=list)
    controllers: list[Any] = field(default_factory=list)

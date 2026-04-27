"""Entry-point-based provider and plugin-descriptor discovery.

``discover_providers`` is the function ``lexigram/src/lexigram/app/factory.py``'s
own docstring already promises: "Provider auto-discovery via entry points is
the responsibility of ``lexigram-plugins``."
"""

from __future__ import annotations

from importlib.metadata import entry_points as _entry_points
from typing import TYPE_CHECKING

from lexigram.contracts.core.constants import EP_PLUGINS, EP_PROVIDERS
from lexigram.contracts.plugins import PluginDescriptor
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.di.provider import Provider

logger = get_logger(__name__)

__all__ = ["discover_plugins", "discover_providers"]


def discover_providers(disabled: set[str] | None = None) -> list[Provider]:
    """Discover and instantiate providers from the ``lexigram.providers`` group.

    Args:
        disabled: Entry-point names to skip (e.g. from
            :func:`lexigram.plugins.state.load_disabled`).

    Returns:
        Instantiated ``Provider`` objects for every enabled, constructible
        entry point. Entries that fail to load, aren't a ``Provider``
        subclass, or require constructor arguments are skipped with a log.
    """
    from lexigram.di.provider import Provider

    disabled = disabled or set()
    found: list[Provider] = []

    for ep in _entry_points(group=EP_PROVIDERS):
        if ep.name in disabled:
            logger.debug("plugins.discovery.skipped_disabled", name=ep.name)
            continue
        try:
            provider_cls = ep.load()
        except Exception:  # noqa: BLE001 — skip bad entry points, continue discovery
            logger.warning("plugins.discovery.entry_point_load_failed", name=ep.name)
            continue
        if not (isinstance(provider_cls, type) and issubclass(provider_cls, Provider)):
            logger.debug(
                "plugins.discovery.not_a_provider",
                name=ep.name,
                loaded=repr(provider_cls),
            )
            continue
        try:
            found.append(provider_cls())
        except TypeError:
            logger.debug(
                "plugins.discovery.skipped_ctor_args",
                name=ep.name,
                reason="requires_constructor_args",
            )

    return found


def discover_plugins() -> list[PluginDescriptor]:
    """Discover all ``PluginDescriptor``s registered under ``EP_PLUGINS``.

    Metadata-only — never imports the plugin's actual ``Provider`` class,
    so this is cheap to call even for listing purposes (e.g. an admin UI).
    """
    found: list[PluginDescriptor] = []
    for ep in _entry_points(group=EP_PLUGINS):
        try:
            descriptor = ep.load()
        except Exception:  # noqa: BLE001 — skip bad entry points, continue discovery
            logger.warning(
                "plugins.discovery.plugin_entry_point_load_failed", name=ep.name
            )
            continue
        if not isinstance(descriptor, PluginDescriptor):
            logger.debug(
                "plugins.discovery.not_a_plugin_descriptor",
                name=ep.name,
                loaded=repr(descriptor),
            )
            continue
        found.append(descriptor)
    return found

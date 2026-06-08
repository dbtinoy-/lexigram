"""Plugin descriptor contract type.

A ``PluginDescriptor`` is metadata-only — discovering it via the
``lexigram.plugins`` entry-point group (``EP_PLUGINS``) never imports or
instantiates the plugin's actual DI ``Provider``. That keeps listing
available plugins (e.g. for an admin UI) cheap even when a plugin's
provider class is heavy to import.
"""

from __future__ import annotations

from dataclasses import dataclass

__all__ = ["PluginDescriptor"]


@dataclass(frozen=True)
class PluginDescriptor:
    """Metadata describing an admin-manageable plugin.

    ``provider_entry_point`` is the entry-point *name* (not dotted path)
    this descriptor maps to within the ``lexigram.providers`` (``EP_PROVIDERS``)
    group — the identifier that goes into the ``disabled`` set passed to
    ``lexigram.plugins.discovery.discover_providers``.
    """

    name: str
    display_name: str
    description: str
    icon: str
    provider_entry_point: str
"""Admin CQRS message types.

Commands are defined canonically in ``lexigram.admin.cqrs.commands``.
Queries are defined in ``lexigram.admin.cqrs.queries``.

The framework command and query buses (``CommandBusImpl`` / ``QueryBusImpl``)
live in ``lexigram-events`` and satisfy ``CommandBusProtocol`` /
``QueryBusProtocol`` from ``lexigram-contracts``.  There are no admin-specific
bus reimplementations.
"""

from __future__ import annotations

from lexigram.admin.cqrs.commands import AdminCommand
from lexigram.admin.cqrs.queries import AdminQuery

__all__ = ["AdminCommand", "AdminQuery"]

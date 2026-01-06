"""CQRS marker protocols for the admin system."""

from __future__ import annotations

from lexigram.contracts.admin.cqrs.command import AdminCommand
from lexigram.contracts.admin.cqrs.query import AdminQuery

__all__ = ["AdminCommand", "AdminQuery"]

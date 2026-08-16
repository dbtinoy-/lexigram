"""Custom GraphQL scalars."""

from __future__ import annotations

from lexigram.graphql.scalars.date import Date
from lexigram.graphql.scalars.datetime import DateTime
from lexigram.graphql.scalars.json import JSON
from lexigram.graphql.scalars.misc import URL, UUID, BigInt, Email, Void
from lexigram.graphql.scalars.time import Time
from lexigram.graphql.scalars.timestamp import Timestamp

__all__ = [
    "JSON",
    "URL",
    "UUID",
    "BigInt",
    "Date",
    "DateTime",
    "Email",
    "Time",
    "Timestamp",
    "Void",
]

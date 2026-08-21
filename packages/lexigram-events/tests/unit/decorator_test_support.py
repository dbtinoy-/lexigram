"""Shared message doubles for event-decorator tests."""

from __future__ import annotations

from dataclasses import dataclass

from typing import cast

import pytest

from lexigram.events.decorators.handlers import (
    HandlerInfo,
    clear_handlers,
    command_handler,
    event_handler,
    get_all_handlers,
    get_handler_info,
    multi_event_handler,
    projection,
    query_handler,
    saga,
)
from lexigram.events.decorators.validation import (
    CQRSValidationError,
    clear_idempotency_cache,
    idempotent,
    validate,
    validate_command,
    validate_query,
)
from lexigram.events.messages.command import Command
from lexigram.events.messages.event import Event
from lexigram.events.messages.query import Query



class _TestCommand(Command):
    """Test command."""

    value: str


class _TestQuery(Query):
    """Test query."""

    param: str


class _TestEvent(Event):
    """Test event."""

    data: str


class _TestSaga:
    """Test saga class."""

    pass


class _TestProjection:
    """Test projection class."""

    pass



"""Db-layer context management.

Provides an injectable ``DbContext`` for request-scoped values
(request ID, tenant, user, rate limits) used by database operations.

Composition-root example::

    from lexigram.primitives.context import create_default_context
    from lexigram.sql.context import (
        DbContext,
        RequestContextManager,
        create_db_context,
    )

    core_ctx = create_default_context()
    db_ctx   = create_db_context(core_ctx=core_ctx)

    async with RequestContextManager(db_ctx, request_id="abc"):
        assert db_ctx.request_id == "abc"
"""

from __future__ import annotations

from lexigram.sql.context.db_context import DbContext, create_db_context
from lexigram.sql.context.keys import (
    DB_KEYS,
    RATE_LIMIT_LIMIT,
    RATE_LIMIT_REMAINING,
    RATE_LIMIT_RESET,
    REQUEST_ID,
    TENANT_ID,
    USER,
    USER_ID,
)
from lexigram.sql.context.manager import RequestContextManager
from lexigram.sql.context.tasks import (
    create_task_with_context,
    run_in_threadpool_with_context,
)

__all__ = [
    # Keys (pure data)
    "DB_KEYS",
    "RATE_LIMIT_LIMIT",
    "RATE_LIMIT_REMAINING",
    "RATE_LIMIT_RESET",
    "REQUEST_ID",
    "TENANT_ID",
    "USER",
    "USER_ID",
    # Classes
    "DbContext",
    "RequestContextManager",
    # Factory
    "create_db_context",
    # Task utilities
    "create_task_with_context",
    "run_in_threadpool_with_context",
]

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.nosql.exceptions import TransactionError
from lexigram.nosql.backends.mongodb.session import mongodb_session, mongodb_transaction


class TestMongoDBSession:
    @pytest.mark.asyncio
    async def test_session_yields_session(self) -> None:
        client = MagicMock()
        session = MagicMock()
        client.start_session = AsyncMock(return_value=session)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)

        async with mongodb_session(client) as s:
            assert s is session

    @pytest.mark.asyncio
    async def test_session_raises_transaction_error(self) -> None:
        client = MagicMock()
        client.start_session = AsyncMock(side_effect=RuntimeError("connection failed"))

        with pytest.raises(TransactionError, match="MongoDB session failed"):
            async with mongodb_session(client):
                pass


class TestMongoDBTransaction:
    @pytest.mark.asyncio
    async def test_transaction_yields_session(self) -> None:
        client = MagicMock()
        session = MagicMock()
        client.start_session = AsyncMock(return_value=session)
        session.__aenter__ = AsyncMock(return_value=session)
        session.__aexit__ = AsyncMock(return_value=False)
        session.start_transaction = MagicMock()
        session.start_transaction.return_value.__aenter__ = AsyncMock()
        session.start_transaction.return_value.__aexit__ = AsyncMock(return_value=False)

        async with mongodb_transaction(client) as s:
            assert s is session
            session.start_transaction.assert_called_once()

    @pytest.mark.asyncio
    async def test_transaction_raises_transaction_error(self) -> None:
        client = MagicMock()
        client.start_session = AsyncMock(side_effect=RuntimeError("tx failed"))

        with pytest.raises(TransactionError, match="MongoDB transaction failed"):
            async with mongodb_transaction(client):
                pass

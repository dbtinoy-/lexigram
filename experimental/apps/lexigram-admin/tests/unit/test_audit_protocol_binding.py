from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from lexigram.contracts.audit import AuditLoggerProtocol
from lexigram.admin.di.sub_providers.auth import AdminAuthSubProvider


class _RecordingContainer(MagicMock):
    def has(self, _contract: type) -> bool:
        return False

    def override(self, contract: type, implementation: object) -> None:
        self.singleton(contract, implementation)


@pytest.mark.asyncio
@pytest.mark.skip(reason="Audit protocol registration not yet implemented in auth subprovider")
async def test_auth_subprovider_registers_framework_audit_protocol() -> None:
    container = _RecordingContainer()
    subprovider = AdminAuthSubProvider(config=None)

    await subprovider.register(container)

    registered_contracts = [call.args[0] for call in container.singleton.call_args_list]
    assert AuditLoggerProtocol in registered_contracts

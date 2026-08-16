from __future__ import annotations

import pytest

from lexigram.testing.compliance import StoreConformanceSuite
from lexigram.testing.fakes import FakeRotatableSecretStore


class TestFakeStoreConformance(StoreConformanceSuite):
    """Run the conformance suite against the fake store."""

    @pytest.fixture
    def make_store(  # type: ignore[override]
        self,
    ) -> type[FakeRotatableSecretStore]:
        return FakeRotatableSecretStore

"""Test that all public API symbols are properly exported from lexigram.testing.

This test validates:
1. All documented fakes are exported
2. All 10 compliance suites are exported
3. All memory implementations are exported
4. All test beds and clients are exported
5. All utility assertions are exported
6. Container and fixture helpers are exported
"""


class TestPublicExports:
    """Verify lexigram.testing exports all documented symbols."""

    def test_all_fakes_are_exported(self) -> None:
        """Verify all 12+ fake doubles are exported from lexigram.testing."""
        import lexigram.testing

        fakes_required = [
            "FakeEventBus",
            "FakeLogger",
            "FakeCache",
            "FakeCommandBus",
            "FakeQueryBus",
            "FakeClock",
            "FakeMetricsCollector",
            "FakeConfig",
            "FakeStateStore",
            "FakeUnitOfWork",
            "Clock",  # Base clock interface
            "SystemClock",  # Real clock implementation
            "LogEntry",  # Log entry type for FakeLogger
        ]

        for fake_name in fakes_required:
            assert hasattr(lexigram.testing, fake_name), (
                f"Missing fake export: {fake_name}"
            )
            # Verify it can actually be imported
            obj = getattr(lexigram.testing, fake_name)
            assert obj is not None, f"Fake import returned None: {fake_name}"

    def test_all_compliance_suites_are_exported(self) -> None:
        """Verify all 9 compliance suites are exported from lexigram.testing.

        The conformance architecture requires all suite types to be discoverable.
        Missing compliance suites means implementations can't be tested properly.
        """
        import lexigram.testing

        compliance_required = [
            "EventBusCompliance",
            "RepositoryCompliance",
            "CacheBackendCompliance",
            "DatabaseProviderCompliance",
            "TaskQueueCompliance",
            "BlobStoreCompliance",
            "SearchEngineCompliance",
            "FlagProviderCompliance",
            "MiddlewareCompliance",
        ]

        for suite_name in compliance_required:
            assert hasattr(lexigram.testing, suite_name), (
                f"Missing compliance suite export: {suite_name}"
            )
            obj = getattr(lexigram.testing, suite_name)
            assert obj is not None, (
                f"Compliance suite import returned None: {suite_name}"
            )

    def test_all_memory_implementations_are_exported(self) -> None:
        """Verify all in-memory implementations are exported.

        Memory implementations are critical for unit testing without
        external infrastructure.
        """
        import lexigram.testing

        memory_required = [
            "InMemoryRepository",
            "InMemoryEventBus",
            "InMemoryCommandBus",
            "InMemoryQueryBus",
            "InMemoryUnitOfWork",
            "InMemoryAuditLogger",
            "InMemoryDistributedLock",
            "InMemoryOutbox",
            "OutboxRelay",
            "InMemoryCacheBackend",
            "MemoryProvider",
        ]

        for impl_name in memory_required:
            assert hasattr(lexigram.testing, impl_name), (
                f"Missing memory implementation export: {impl_name}"
            )

    def test_all_test_beds_are_exported(self) -> None:
        """Verify all test bed and client classes are exported."""
        import lexigram.testing

        testbed_required = [
            "AppTestBed",
            "TestEnvironment",
            "WebTestBed",
            "WebTestClient",
            "DatabaseTestBed",
            "DatabaseTestClient",
            "AITestBed",
            "AITestClient",
            "TaskTestBed",
            "TaskTestClient",
        ]

        for testbed_name in testbed_required:
            assert hasattr(lexigram.testing, testbed_name), (
                f"Missing test bed export: {testbed_name}"
            )

    def test_all_container_helpers_are_exported(self) -> None:
        """Verify container helpers are exported."""
        import lexigram.testing

        container_required = [
            "LexigramContainerHarness",  # Canonical name (replaces TestContainer)
            "ContainerTestFixture",
            "ContainerFactory",
            "override",
        ]

        for helper_name in container_required:
            assert hasattr(lexigram.testing, helper_name), (
                f"Missing container helper export: {helper_name}"
            )

    def test_all_assertions_are_exported(self) -> None:
        """Verify all test assertion helpers are exported."""
        import lexigram.testing

        assertions_required = [
            "assert_result_ok",
            "assert_result_err",
            "assert_ok",
            "assert_err",
            "assert_healthy",
            "assert_all_ok",
            "TestAssertions",
            "TestDataFactory",
            "AsyncTestHelper",
        ]

        for assertion_name in assertions_required:
            assert hasattr(lexigram.testing, assertion_name), (
                f"Missing assertion helper export: {assertion_name}"
            )

    def test_snapshot_utilities_are_exported(self) -> None:
        """Verify snapshot testing utilities are exported."""
        import lexigram.testing

        snapshot_required = [
            "SnapshotAsserter",
            "SnapshotMismatchError",
        ]

        for snapshot_name in snapshot_required:
            assert hasattr(lexigram.testing, snapshot_name), (
                f"Missing snapshot utility export: {snapshot_name}"
            )

    def test_markers_and_probes_are_exported(self) -> None:
        """Verify integration markers and service probes are exported."""
        import lexigram.testing

        markers_required = [
            "requires_redis",
            "requires_postgres",
            "requires_rabbitmq",
            "ServiceProbe",
        ]

        for marker_name in markers_required:
            assert hasattr(lexigram.testing, marker_name), (
                f"Missing marker/probe export: {marker_name}"
            )

    def test_exported_symbols_are_in_all(self) -> None:
        """Verify all documented symbols appear in __all__."""
        import lexigram.testing

        required_in_all = [
            "LexigramContainerHarness",  # Canonical name (replaces TestContainer)
            "ContainerFactory",
            "FakeEventBus",
            "FakeLogger",
            "CacheBackendCompliance",
            "SnapshotAsserter",
            "AppTestBed",
        ]

        all_list = getattr(lexigram.testing, "__all__", [])
        for symbol in required_in_all:
            assert symbol in all_list, f"Symbol {symbol} not in __all__: {all_list}"

    def test_version_is_accessible(self) -> None:
        """Verify __version__ is accessible."""
        import lexigram.testing

        version = getattr(lexigram.testing, "__version__", None)
        assert version is not None, "Module __version__ not accessible"
        assert isinstance(version, str), "__version__ should be a string"
        assert len(version) > 0, "__version__ should not be empty"

    def test_ai_mocks_are_exported(self) -> None:
        """Verify optional AI mock classes are exported (if available).

        These may not be available if lexigram-ai is not installed.
        """
        import lexigram.testing

        # These are optional — should not fail if not available
        ai_mocks = [
            "MockLLMClient",
            "MockVectorStore",
            "MockClassifier",
        ]

        for mock_name in ai_mocks:
            # Try to access; if it fails, that's okay (optional dependency)
            try:
                obj = getattr(lexigram.testing, mock_name)
                assert obj is not None, f"AI mock import returned None: {mock_name}"
            except AttributeError:
                # Optional dependency not installed
                pass

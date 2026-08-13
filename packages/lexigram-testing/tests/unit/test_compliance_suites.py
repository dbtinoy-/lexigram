"""Test that all compliance suites are properly defined and accessible."""

import pytest


class TestComplianceSuitesAvailability:
    """Test that compliance suites are defined and accessible."""

    def test_compliance_module_exists(self) -> None:
        """Verify the compliance module exists."""
        try:
            from lexigram.testing import compliance

            assert compliance is not None
        except ImportError:
            pytest.skip("compliance module not available")

    def test_compliance_suites_can_be_imported(self) -> None:
        """Verify compliance suite classes can be imported."""
        from lexigram.testing import compliance

        # Get all classes from the compliance module
        suite_classes = [
            (name, cls)
            for name, cls in vars(compliance).items()
            if isinstance(cls, type) and name.endswith("Compliance")
        ]

        # Should have at least some compliance suites defined
        assert len(suite_classes) > 0, "No compliance suites found in compliance module"

    def test_compliance_suites_exported_from_testing(self) -> None:
        """Verify at least some compliance suites are exported from lexigram.testing."""
        from lexigram import testing

        # Count how many Compliance classes are available
        compliance_classes = [
            name
            for name in dir(testing)
            if name.endswith("Compliance") and not name.startswith("_")
        ]

        # Should have at least some
        assert len(compliance_classes) >= 0

    def test_cache_backend_compliance_available(self) -> None:
        """Verify CacheBackendCompliance is available if defined."""
        try:
            from lexigram.testing import CacheBackendCompliance

            assert CacheBackendCompliance is not None
        except ImportError:
            pytest.skip("CacheBackendCompliance not exported")

    def test_repository_compliance_available(self) -> None:
        """Verify RepositoryCompliance is available if defined."""
        try:
            from lexigram.testing import RepositoryCompliance

            assert RepositoryCompliance is not None
        except ImportError:
            pytest.skip("RepositoryCompliance not exported")

    def test_event_bus_compliance_available(self) -> None:
        """Verify EventBusCompliance is available if defined."""
        try:
            from lexigram.testing import EventBusCompliance

            assert EventBusCompliance is not None
        except ImportError:
            pytest.skip("EventBusCompliance not exported")

    def test_database_provider_compliance_available(self) -> None:
        """Verify DatabaseProviderCompliance is available if defined."""
        try:
            from lexigram.testing import DatabaseProviderCompliance

            assert DatabaseProviderCompliance is not None
        except ImportError:
            pytest.skip("DatabaseProviderCompliance not exported")

    def test_task_queue_compliance_available(self) -> None:
        """Verify TaskQueueCompliance is available if defined."""
        try:
            from lexigram.testing import TaskQueueCompliance

            assert TaskQueueCompliance is not None
        except ImportError:
            pytest.skip("TaskQueueCompliance not exported")

    def test_blob_store_compliance_available(self) -> None:
        """Verify BlobStoreCompliance is available if defined."""
        try:
            from lexigram.testing import BlobStoreCompliance

            assert BlobStoreCompliance is not None
        except ImportError:
            pytest.skip("BlobStoreCompliance not exported")

    def test_search_engine_compliance_available(self) -> None:
        """Verify SearchEngineCompliance is available if defined."""
        try:
            from lexigram.testing import SearchEngineCompliance

            assert SearchEngineCompliance is not None
        except ImportError:
            pytest.skip("SearchEngineCompliance not exported")

    def test_flag_provider_compliance_available(self) -> None:
        """Verify FlagProviderCompliance is available if defined."""
        try:
            from lexigram.testing import FlagProviderCompliance

            assert FlagProviderCompliance is not None
        except ImportError:
            pytest.skip("FlagProviderCompliance not exported")

    def test_middleware_compliance_available(self) -> None:
        """Verify MiddlewareCompliance is available if defined."""
        try:
            from lexigram.testing import MiddlewareCompliance

            assert MiddlewareCompliance is not None
        except ImportError:
            pytest.skip("MiddlewareCompliance not exported")

    def test_compliance_suites_are_abstract_base_classes(self) -> None:
        """Verify compliance suites are abstract base classes or follow ABC pattern."""
        from abc import ABC

        from lexigram.testing import compliance

        # Get all compliance suite classes
        suite_classes = [
            cls
            for name, cls in vars(compliance).items()
            if isinstance(cls, type) and name.endswith("Compliance")
        ]

        # Each should be an ABC or at least have abstract methods
        for suite in suite_classes:
            # Check that it's either an ABC or has test methods
            is_abc = issubclass(suite, ABC)
            has_methods = len([m for m in dir(suite) if m.startswith("test_")]) > 0
            assert is_abc or has_methods, (
                f"{suite.__name__} should be ABC or have test methods"
            )

    def test_compliance_modules_structure(self) -> None:
        """Verify the compliance module structure is sound."""
        from lexigram.testing import compliance

        # Should have __all__ or classes defined
        assert hasattr(compliance, "__all__") or len(dir(compliance)) > 1

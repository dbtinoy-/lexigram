"""Testing utilities and helpers."""

from __future__ import annotations

from lexigram.testing.lib.assertions import (
    TestAssertions,
    assert_all_ok,
    assert_err,
    assert_healthy,
    assert_ok,
    assert_result_err,
    assert_result_err_contains,
    assert_result_err_type,
    assert_result_maps_to,
    assert_result_ok,
    assert_result_ok_value,
)
from lexigram.testing.lib.async_helper import AsyncTestHelper
from lexigram.testing.lib.factory import TestDataFactory

# Module-level convenience instances
test_assertions = TestAssertions()
test_data_factory = TestDataFactory()

__all__ = [
    "AsyncTestHelper",
    "TestAssertions",
    "TestDataFactory",
    "assert_all_ok",
    "assert_err",
    "assert_healthy",
    "assert_ok",
    "assert_result_err",
    "assert_result_err_contains",
    "assert_result_err_type",
    "assert_result_maps_to",
    "assert_result_ok",
    "assert_result_ok_value",
    "test_assertions",
    "test_data_factory",
]

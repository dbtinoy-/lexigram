"""Tests for shared admin contributor boot-failure summaries."""

from __future__ import annotations

from lexigram.contracts.admin.contributor_boot import (
    summarize_contributor_boot_failure,
)
from lexigram.contracts.exceptions.container import (
    ScopedResolutionError,
    UnresolvableDependencyError,
)


def test_expected_dependency_failure_uses_dependency_detail() -> None:
    failure = summarize_contributor_boot_failure(
        UnresolvableDependencyError(
            "formatted message\n  → Fix: register it",
            dependency="CacheBackendProtocol",
        )
    )

    assert failure.expected is True
    assert failure.reason == "required service not registered"
    assert failure.summary == "CacheBackendProtocol"


def test_expected_dependency_failure_never_uses_multiline_error_text() -> None:
    failure = summarize_contributor_boot_failure(
        UnresolvableDependencyError("missing\n  → Fix: do something")
    )

    assert failure.expected is True
    assert failure.summary == "unspecified dependency"
    assert "LEX_ERR" not in failure.summary
    assert "\n" not in failure.summary


def test_dependency_error_subclasses_are_expected() -> None:
    failure = summarize_contributor_boot_failure(
        ScopedResolutionError(service="SessionService")
    )

    assert failure.expected is True
    assert failure.summary == "SessionService"


def test_unexpected_failure_is_one_line_and_bounded() -> None:
    failure = summarize_contributor_boot_failure(
        RuntimeError("first line\nsecond line\twith whitespace"),
        max_length=24,
    )

    assert failure.expected is False
    assert failure.reason == "contributor boot hook failed"
    assert failure.summary == "first line second line…"
    assert len(failure.summary) <= 24
    assert "\n" not in failure.summary


def test_empty_unexpected_failure_falls_back_to_type_name() -> None:
    failure = summarize_contributor_boot_failure(ValueError())

    assert failure.expected is False
    assert failure.summary == "ValueError"

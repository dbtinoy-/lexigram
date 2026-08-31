"""Regression tests for creating records whose id is server-generated.

Protected columns (``id``, ``tenant_id``, ``created_at``, ``updated_at``) are
stripped from submitted form data so a form can never assign them. Dataclass
models normally still declare those columns as required constructor
arguments, so validating the stripped mapping by calling the model used to
raise ``TypeError`` and reject every create as a validation failure.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

import pytest

from lexigram.admin.exceptions import AdminValidationError
from lexigram.admin.controllers.resource import ResourceController


@dataclass
class GeneratedIdRecord:
    """Model whose identity and timestamps are assigned by the store."""

    id: int
    name: str
    email: str
    created_at: str
    status: str = "active"


@dataclass
class DefaultedRecord:
    """Model that supplies its own defaults for server-owned columns."""

    name: str
    id: int = 0
    tags: list[str] = field(default_factory=list)


class GeneratedIdController(ResourceController[GeneratedIdRecord]):
    """Controller bound to a model with required server-owned columns."""


class DefaultedController(ResourceController[DefaultedRecord]):
    """Controller bound to a model with defaulted server-owned columns."""


class TestCreateValidationWithGeneratedId:
    """Server-owned columns must not block create validation."""

    def test_create_validates_without_submitted_id(self) -> None:
        controller = GeneratedIdController()

        validated = controller.validate_create(
            {"name": "New Person", "email": "new@test.com"}
        )

        assert validated == {"name": "New Person", "email": "new@test.com"}

    def test_server_owned_columns_are_not_forwarded(self) -> None:
        controller = GeneratedIdController()

        validated = controller.validate_create(
            {"name": "New Person", "email": "new@test.com"}
        )

        for protected in ("id", "created_at", "tenant_id", "updated_at"):
            assert protected not in validated

    def test_submitted_id_is_ignored(self) -> None:
        """A client cannot assign identity by smuggling it through the form."""
        controller = GeneratedIdController()

        validated = controller.validate_create(
            {"id": "999", "name": "New Person", "email": "new@test.com"}
        )

        assert "id" not in validated

    def test_genuinely_missing_field_still_fails(self) -> None:
        """The relaxation must not mask real, user-fixable validation errors."""
        controller = GeneratedIdController()

        with pytest.raises(AdminValidationError):
            controller.validate_create({"name": "No Email Supplied"})

    def test_defaulted_model_is_unaffected(self) -> None:
        controller = DefaultedController()

        validated = controller.validate_create({"name": "Someone"})

        assert validated == {"name": "Someone"}


class TestMissingProtectedArguments:
    """The probe only fills required, protected, absent parameters."""

    def test_reports_required_protected_parameter(self) -> None:
        missing = GeneratedIdController._missing_protected_arguments(
            GeneratedIdRecord, {"name": "x", "email": "y"}
        )

        assert missing == {"id", "created_at"}

    def test_ignores_supplied_parameters(self) -> None:
        missing = GeneratedIdController._missing_protected_arguments(
            GeneratedIdRecord, {"name": "x", "email": "y", "id": 1, "created_at": "now"}
        )

        assert missing == set()

    def test_ignores_defaulted_parameters(self) -> None:
        missing = DefaultedController._missing_protected_arguments(
            DefaultedRecord, {"name": "x"}
        )

        assert missing == set()

    def test_ignores_unprotected_required_parameters(self) -> None:
        """Required business fields stay the user's responsibility."""
        missing = GeneratedIdController._missing_protected_arguments(
            GeneratedIdRecord, {"name": "x"}
        )

        assert "email" not in missing

    def test_uninspectable_model_is_tolerated(self) -> None:
        class Opaque:
            """Callable whose signature cannot be introspected."""

            __signature__: Any = property(lambda self: 1 / 0)

        missing = GeneratedIdController._missing_protected_arguments(Opaque, {})

        assert missing == set()

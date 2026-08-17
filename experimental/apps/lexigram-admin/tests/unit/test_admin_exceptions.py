"""Tests for admin exceptions."""

import pytest

from lexigram.admin.exceptions import (
    AdminDataError,
    AdminError,
    AdminValidationError,
    ConflictError,
    DataError,
    ErrorCode,
    NotFoundError,
    NotificationError,
    PermissionDeniedError,
)
from lexigram.contracts.exceptions import DomainError, LexigramError, ValidationError


class TestErrorCode:
    """Tests for ErrorCode StrEnum."""

    def test_auth_codes(self) -> None:
        assert ErrorCode.AUTH_INVALID_TOKEN.value == "AUTH_INVALID_TOKEN"
        assert ErrorCode.AUTH_SESSION_EXPIRED.value == "AUTH_SESSION_EXPIRED"
        assert ErrorCode.AUTH_PERMISSION_DENIED.value == "AUTH_PERMISSION_DENIED"
        assert ErrorCode.AUTH_NOT_AUTHENTICATED.value == "AUTH_NOT_AUTHENTICATED"

    def test_resource_codes(self) -> None:
        assert ErrorCode.RESOURCE_NOT_FOUND.value == "RESOURCE_NOT_FOUND"
        assert ErrorCode.RESOURCE_CONFLICT.value == "RESOURCE_CONFLICT"

    def test_validation_code(self) -> None:
        assert ErrorCode.VALIDATION_FAILED.value == "VALIDATION_FAILED"

    def test_is_str_enum(self) -> None:
        assert isinstance(ErrorCode.AUTH_INVALID_TOKEN, str)


class TestAdminError:
    """Tests for AdminError base exception."""

    def test_inherits_from_lexigram_error(self) -> None:
        assert issubclass(AdminError, LexigramError)

    def test_can_be_raised(self) -> None:
        with pytest.raises(AdminError):
            raise AdminError("test error")


class TestNotFoundError:
    """Tests for NotFoundError exception."""

    def test_inherits_from_domain_error(self) -> None:
        assert issubclass(NotFoundError, DomainError)

    def test_can_be_raised(self) -> None:
        with pytest.raises(NotFoundError):
            raise NotFoundError("resource not found")


class TestPermissionDeniedError:
    """Tests for PermissionDeniedError exception."""

    def test_inherits_from_domain_error(self) -> None:
        assert issubclass(PermissionDeniedError, DomainError)

    def test_can_be_raised(self) -> None:
        with pytest.raises(PermissionDeniedError):
            raise PermissionDeniedError("permission denied")


class TestConflictError:
    """Tests for ConflictError exception."""

    def test_inherits_from_domain_error(self) -> None:
        assert issubclass(ConflictError, DomainError)

    def test_can_be_raised(self) -> None:
        with pytest.raises(ConflictError):
            raise ConflictError("resource conflict")


class TestAdminValidationError:
    """Tests for AdminValidationError exception."""

    def test_inherits_from_validation_error(self) -> None:
        assert issubclass(AdminValidationError, ValidationError)

    def test_can_be_raised(self) -> None:
        with pytest.raises(AdminValidationError):
            raise AdminValidationError("validation failed")


class TestDataError:
    """Tests for DataError exception."""

    def test_inherits_from_domain_error(self) -> None:
        assert issubclass(DataError, DomainError)

    def test_can_be_raised(self) -> None:
        with pytest.raises(DataError):
            raise DataError("data error")


class TestAdminDataError:
    """Tests for AdminDataError exception."""

    def test_inherits_from_admin_error(self) -> None:
        assert issubclass(AdminDataError, AdminError)

    def test_can_be_raised(self) -> None:
        with pytest.raises(AdminDataError):
            raise AdminDataError("data operation failed")


class TestNotificationError:
    """Tests for NotificationError exception."""

    def test_inherits_from_domain_error(self) -> None:
        assert issubclass(NotificationError, DomainError)

    def test_can_be_raised(self) -> None:
        with pytest.raises(NotificationError):
            raise NotificationError("notification failed")
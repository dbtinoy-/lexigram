"""Unit tests for lexigram core security exceptions.

Adapted from lexigram-security/tests/unit/test_security_exceptions.py.
The critical addition is test_exceptions_module_is_core_package which
verifies that the module resolves to lexigram core, not lexigram-security.
That test fails before lexigram/src/lexigram/security/ exists and passes
once the core package is created (core's __path__ position takes priority).
"""

from __future__ import annotations

import importlib.util

from lexigram.contracts.exceptions import LexigramError
from lexigram.security.exceptions import (
    DecryptionError,
    EncryptionError,
    MiddlewareGuardError,
    SecretAccessError,
    SecretError,
    SecretNotFoundError,
    SecurityError,
)


class TestSecurityExceptionHierarchy:
    """Tests for security exception hierarchy."""

    def test_security_error_inherits_from_lexigram_error(self) -> None:
        assert issubclass(SecurityError, LexigramError)

    def test_secret_error_inherits_from_security_error(self) -> None:
        assert issubclass(SecretError, SecurityError)

    def test_secret_not_found_error_inherits_from_secret_error(self) -> None:
        assert issubclass(SecretNotFoundError, SecretError)

    def test_secret_access_error_inherits_from_secret_error(self) -> None:
        assert issubclass(SecretAccessError, SecretError)

    def test_guard_error_inherits_from_lexigram_error(self) -> None:
        assert issubclass(MiddlewareGuardError, LexigramError)

    def test_encryption_error_inherits_from_security_error(self) -> None:
        assert issubclass(EncryptionError, SecurityError)

    def test_decryption_error_inherits_from_security_error(self) -> None:
        assert issubclass(DecryptionError, SecurityError)


class TestSecurityError:
    """Tests for SecurityError."""

    def test_security_error_default_message(self) -> None:
        error = SecurityError()
        assert error.message is not None


class TestSecretError:
    """Tests for SecretError."""

    def test_secret_error_default_message(self) -> None:
        error = SecretError()
        assert error.message is not None


class TestSecretNotFoundError:
    """Tests for SecretNotFoundError."""

    def test_secret_not_found_error_inherits(self) -> None:
        assert issubclass(SecretNotFoundError, SecretError)


class TestSecretAccessError:
    """Tests for SecretAccessError."""

    def test_secret_access_error_inherits(self) -> None:
        assert issubclass(SecretAccessError, SecretError)


class TestMiddlewareGuardError:
    """Tests for MiddlewareGuardError (from contracts)."""

    def test_guard_error_inherits(self) -> None:
        assert issubclass(MiddlewareGuardError, LexigramError)

    def test_guard_error_default_message(self) -> None:
        error = MiddlewareGuardError()
        assert error.message is not None


class TestExceptionAllExports:
    """Tests to verify __all__ exports."""

    def test_all_contains_all_exceptions(self) -> None:
        from lexigram.security import exceptions as exc_module

        expected = [
            "DecryptionError",
            "EncryptionError",
            "MiddlewareGuardError",
            "SecretAccessError",
            "SecretError",
            "SecretNotFoundError",
            "SecurityError",
        ]
        for item in expected:
            assert item in exc_module.__all__


class TestExceptionsModuleIsCore:
    """Verify the exceptions module resolves to lexigram core, not lexigram-security.

    This test is the TDD signal for Task 1: it fails while only
    lexigram-security exists, and passes once lexigram/src/lexigram/security/
    is created (core takes priority in lexigram.__path__).
    """

    def test_exceptions_module_is_core_package(self) -> None:
        spec = importlib.util.find_spec("lexigram.security.exceptions")
        assert spec is not None, "lexigram.security.exceptions must be importable"
        assert spec.origin is not None, "module must have a known origin path"
        assert "lexigram-security" not in spec.origin, (
            f"Expected lexigram.security.exceptions to resolve to lexigram core, "
            f"but it resolved to: {spec.origin!r}. "
            f"Create lexigram/src/lexigram/security/exceptions.py to fix this."
        )

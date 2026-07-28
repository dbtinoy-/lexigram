from __future__ import annotations

import importlib

import pytest

EXPECTED_MODULE_EXPORTS: dict[str, list[str]] = {
    "lexigram.contracts.core.lifecycle": [
        "GracefulShutdownProtocol",
        "OnApplicationBootstrapProtocol",
        "OnApplicationShutdownProtocol",
        "OnBeforeShutdownProtocol",
        "OnConfigReloadProtocol",
        "OnModuleInitProtocol",
    ],
    "lexigram.contracts.domain.base": ["ID", "DomainModelProtocol"],
    "lexigram.contracts.domain.events": ["DomainEvent"],
    "lexigram.contracts.domain.pagination": [
        "CursorPage",
        "CursorPageProtocol",
        "OffsetPageProtocol",
        "T",
    ],
    "lexigram.contracts.domain.services": [
        "DomainServiceProtocol",
        "PolicyProtocol",
        "PolicyViolationProtocol",
        "T",
        "T_co",
    ],
    "lexigram.contracts.exceptions.components": [
        "ComponentConnectionError",
        "ComponentError",
        "DriverNotAvailableError",
        "KeyExistsError",
        "KeyNotFoundError",
        "LockAcquisitionError",
        "LockNotHeldError",
        "PubSubError",
        "SecretNotFoundError",
    ],
    "lexigram.contracts.exceptions.domain": [
        "AuthenticationError",
        "AuthorizationError",
        "ConflictError",
        "DomainError",
        "FieldError",
        "MappingError",
        "NotFoundError",
        "PermissionDeniedError",
        "RateLimitError",
        "SerializationError",
        "ValidationError",
        "WebError",
    ],
    "lexigram.contracts.exceptions.infra": [
        "ConstraintError",
        "DatabaseError",
        "DuplicateKeyError",
        "InfrastructureError",
        "IntegrityError",
        "LockConflictError",
        "LockError",
        "MigrationError",
        "NoPrimaryBackendError",
        "RegistryAlreadyExistsError",
        "RegistryError",
        "RegistryKeyError",
    ],
    "lexigram.contracts.lib.time": ["utcnow"],
}


@pytest.mark.parametrize(
    ("module_path", "expected_exports"),
    EXPECTED_MODULE_EXPORTS.items(),
)
def test_module_declares_explicit_all(
    module_path: str,
    expected_exports: list[str],
) -> None:
    module = importlib.import_module(module_path)
    exported = getattr(module, "__all__", None)

    assert isinstance(exported, list)
    assert exported == expected_exports
    for name in exported:
        assert not name.startswith("_")
        assert hasattr(module, name)

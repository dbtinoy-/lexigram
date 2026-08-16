"""Lexigram audit — unified audit trail with retention and HMAC verification."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.audit.admin.contributor import AuditAdminContributor
    from lexigram.audit.config import AuditConfig
    from lexigram.audit.di.bundle_provider import AuditBundleProvider
    from lexigram.audit.logging.logger import AuditLogger
    from lexigram.audit.module import AuditModule
    from lexigram.audit.retention.policy import PolicyBasedRetention
    from lexigram.audit.retention.purge import AuditPurger
    from lexigram.audit.store.memory import InMemoryAuditStore
    from lexigram.audit.verification.checksum import (
        compute_audit_checksum,
        verify_audit_checksum,
    )
    from lexigram.audit.verification.verifier import AuditVerifier

_LAZY_IMPORTS: dict[str, str] = {
    "AuditAdminContributor": "lexigram.audit.admin.contributor",
    "AuditConfig": "lexigram.audit.config",
    "AuditBundleProvider": "lexigram.audit.di.bundle_provider",
    "AuditLogger": "lexigram.audit.logging.logger",
    "AuditModule": "lexigram.audit.module",
    "PolicyBasedRetention": "lexigram.audit.retention.policy",
    "AuditPurger": "lexigram.audit.retention.purge",
    "InMemoryAuditStore": "lexigram.audit.store.memory",
    "compute_audit_checksum": "lexigram.audit.verification.checksum",
    "verify_audit_checksum": "lexigram.audit.verification.checksum",
    "AuditVerifier": "lexigram.audit.verification.verifier",
}


def __getattr__(name: str) -> object:
    if name in _LAZY_IMPORTS:
        import importlib

        mod = importlib.import_module(_LAZY_IMPORTS[name])
        return getattr(mod, name)
    raise AttributeError(f"module 'lexigram.audit' has no attribute {name!r}")


__all__ = list(_LAZY_IMPORTS)

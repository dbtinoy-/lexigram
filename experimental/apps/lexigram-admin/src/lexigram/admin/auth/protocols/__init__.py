"""Admin authentication service protocols.

All protocols remain in lexigram-admin (not lexigram-contracts) because they
are admin-specific and not consumed by other extension packages.

``AdminAuditLogServiceProtocol`` extends the framework-wide
``AuditLoggerProtocol`` from ``lexigram.contracts.audit`` so that admin audit
implementations satisfy the cross-package contract.
"""

from __future__ import annotations

from lexigram.admin.auth.protocols.attempt_service import (
    AdminLoginAttemptServiceProtocol as AdminLoginAttemptServiceProtocol,
)
from lexigram.admin.auth.protocols.audit import (
    AdminAuditLogServiceProtocol as AdminAuditLogServiceProtocol,
)
from lexigram.admin.auth.protocols.audit import (
    AdminAuditLogStoreProtocol as AdminAuditLogStoreProtocol,
)
from lexigram.admin.auth.protocols.csrf import (
    AdminCsrfServiceProtocol as AdminCsrfServiceProtocol,
)
from lexigram.admin.auth.protocols.email_otp import (
    AdminEmailOtpServiceProtocol as AdminEmailOtpServiceProtocol,
)
from lexigram.admin.auth.protocols.email_otp import (
    AdminEmailOtpStoreProtocol as AdminEmailOtpStoreProtocol,
)
from lexigram.admin.auth.protocols.email_verification import (
    AdminEmailVerificationServiceProtocol as AdminEmailVerificationServiceProtocol,
)
from lexigram.admin.auth.protocols.email_verification import (
    AdminEmailVerificationStoreProtocol as AdminEmailVerificationStoreProtocol,
)
from lexigram.admin.auth.protocols.mfa import (
    AdminMfaServiceProtocol as AdminMfaServiceProtocol,
)
from lexigram.admin.auth.protocols.mfa import (
    AdminMfaStoreProtocol as AdminMfaStoreProtocol,
)
from lexigram.admin.auth.protocols.password_reset import (
    AdminPasswordResetServiceProtocol as AdminPasswordResetServiceProtocol,
)
from lexigram.admin.auth.protocols.password_reset import (
    AdminPasswordResetTokenStoreProtocol as AdminPasswordResetTokenStoreProtocol,
)
from lexigram.admin.auth.protocols.policy import (
    AdminPasswordPolicyServiceProtocol as AdminPasswordPolicyServiceProtocol,
)
from lexigram.admin.auth.protocols.service import (
    AdminAuthServiceProtocol as AdminAuthServiceProtocol,
)
from lexigram.admin.auth.protocols.session import (
    AdminSessionServiceProtocol as AdminSessionServiceProtocol,
)
from lexigram.admin.auth.protocols.user_store import (
    AdminAccountLockoutStoreProtocol as AdminAccountLockoutStoreProtocol,
)
from lexigram.admin.auth.protocols.user_store import (
    AdminLoginAttemptStoreProtocol as AdminLoginAttemptStoreProtocol,
)

__all__ = [
    "AdminAccountLockoutStoreProtocol",
    "AdminAuditLogServiceProtocol",
    "AdminAuditLogStoreProtocol",
    "AdminAuthServiceProtocol",
    "AdminCsrfServiceProtocol",
    "AdminEmailOtpServiceProtocol",
    "AdminEmailOtpStoreProtocol",
    "AdminEmailVerificationServiceProtocol",
    "AdminEmailVerificationStoreProtocol",
    "AdminLoginAttemptServiceProtocol",
    "AdminLoginAttemptStoreProtocol",
    "AdminMfaServiceProtocol",
    "AdminMfaStoreProtocol",
    "AdminPasswordPolicyServiceProtocol",
    "AdminPasswordResetServiceProtocol",
    "AdminPasswordResetTokenStoreProtocol",
    "AdminSessionServiceProtocol",
]

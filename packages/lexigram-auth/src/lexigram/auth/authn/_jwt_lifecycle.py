"""Token lifecycle mixin for :class:`~lexigram.auth.authn.jwt.JWTTokenManager`.

Aggregates the verification, refresh-rotation, and revocation seams into
the single ``_JWTLifecycleMixin`` consumed by ``JWTTokenManager``.

This module is an internal implementation detail; import
:class:`~lexigram.auth.authn.jwt.JWTTokenManager` directly.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import TYPE_CHECKING, Any

from lexigram.auth.authn._binding import TokenBindingConfig
from lexigram.auth.authn._jwt_refresh import _JWTRefreshMixin
from lexigram.auth.authn.blacklist import JWTBlacklist
from lexigram.auth.models import AuthToken
from lexigram.auth.models.user import User

if TYPE_CHECKING:
    from lexigram.contracts.audit import AuditLoggerProtocol
    from lexigram.contracts.core import HookRegistryProtocol
    from lexigram.logging import LoggerProtocol as Logger


class _JWTLifecycleMixin(_JWTRefreshMixin):
    """Aggregate mixin for JWT token verification and lifecycle methods.

    Composes the verification, refresh-rotation, and revocation seams
    (``_JWTRefreshMixin`` extends ``_JWTRevocationMixin``, which extends
    ``_JWTVerificationMixin``). All public attributes referenced by the
    composed seams are initialised by ``JWTTokenManager.__init__``; they
    are declared below as class-level annotations solely to satisfy static
    type checkers.
    """

    # ── Attributes set by JWTTokenManager.__init__ ───────────────────────────
    algorithm: str
    access_expiration_hours: int
    refresh_expiration_days: int
    _required_audience: str | None
    _binding_config: TokenBindingConfig | None
    _blacklist_mgr: JWTBlacklist
    _verification_cache: OrderedDict[str, str]
    _verified_by_key: dict[str, str]
    logger: Logger
    _audit_logger: AuditLoggerProtocol | None
    _hooks: HookRegistryProtocol | None

    @property
    def keys(self) -> dict[str, Any]:  # pragma: no cover
        """Live key material — provided by JWTTokenManager."""
        raise NotImplementedError

    @property
    def current_key_id(self) -> str:  # pragma: no cover
        """Active signing key ID — provided by JWTTokenManager."""
        raise NotImplementedError

    def _get_verification_key(self, kid: str) -> str:  # pragma: no cover
        """Return raw verification key — provided by JWTTokenManager."""
        raise NotImplementedError

    def create_token_pair(  # pragma: no cover
        self,
        user: User,
        additional_claims: dict[str, Any] | None = None,
        binding_context: dict[str, str] | None = None,
    ) -> AuthToken:
        """Create token pair — provided by _JWTCreationMixin."""
        raise NotImplementedError

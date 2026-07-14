"""HTTP security public API for Lexigram Web."""

from __future__ import annotations

from lexigram.web.middleware.security import SecurityHeadersMiddleware
from lexigram.web.security.config import (
    CORSConfig,
    CrossOriginConfig,
    CSPConfig,
    CSRFConfig,
    HSTSConfig,
    SecurityConfig,
    SecurityHeadersConfig,
)
from lexigram.web.security.context import SecurityContext, get_security_context
from lexigram.web.security.cors.middleware import CORSMiddleware, CORSMiddlewareFactory
from lexigram.web.security.csp.builder import CSPPolicy
from lexigram.web.security.csrf.middleware import CSRFProtectionMiddleware
from lexigram.web.security.guards import (
    AuthGuard,
    GuardProtocol,
    PermissionGuard,
    RoleGuard,
    use_guards,
)

__all__ = [
    "AuthGuard",
    "CORSConfig",
    "CORSMiddleware",
    "CORSMiddlewareFactory",
    "CSPConfig",
    "CSPPolicy",
    "CSRFConfig",
    "CSRFProtectionMiddleware",
    "CrossOriginConfig",
    "GuardProtocol",
    "HSTSConfig",
    "PermissionGuard",
    "RoleGuard",
    "SecurityConfig",
    "SecurityContext",
    "SecurityHeadersConfig",
    "SecurityHeadersMiddleware",
    "get_security_context",
    "use_guards",
]

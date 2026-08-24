"""Web configuration facade.

Re-exports every public name so that
``from lexigram.web.config import X`` continues to work unchanged.
"""

from lexigram.web.config.api_docs import (
    APIDocsConfig as APIDocsConfig,
)
from lexigram.web.config.api_docs import (
    StaticFileConfig as StaticFileConfig,
)
from lexigram.web.config.provider import WebProviderConfig as WebProviderConfig
from lexigram.web.config.rate_limit import (
    RateLimitConfig as RateLimitConfig,
)
from lexigram.web.config.rate_limit import (
    RateLimitRuleConfig as RateLimitRuleConfig,
)
from lexigram.web.config.rate_limit import (
    RoleGuardConfig as RoleGuardConfig,
)
from lexigram.web.config.rate_limit import (
    RoleGuardRuleConfig as RoleGuardRuleConfig,
)
from lexigram.web.config.server import ServerConfig as ServerConfig
from lexigram.web.config.top_level import WebConfig as WebConfig
from lexigram.web.security.config import (
    CORSConfig as CORSConfig,
)
from lexigram.web.security.config import (
    CrossOriginConfig as CrossOriginConfig,
)
from lexigram.web.security.config import (
    CSPConfig as CSPConfig,
)
from lexigram.web.security.config import (
    CSRFConfig as CSRFConfig,
)
from lexigram.web.security.config import (
    HSTSConfig as HSTSConfig,
)
from lexigram.web.security.config import (
    SecurityConfig as SecurityConfig,
)


def __getattr__(name: str) -> object:  # noqa: ANN001
    if name == "VersioningStrategy":
        from lexigram.web.routing.versioning import VersioningStrategy

        return VersioningStrategy
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = [
    "CORSConfig",
    "CrossOriginConfig",
    "CSPConfig",
    "CSRFConfig",
    "HSTSConfig",
    "RateLimitConfig",
    "RateLimitRuleConfig",
    "RoleGuardConfig",
    "RoleGuardRuleConfig",
    "SecurityConfig",
    "ServerConfig",
    "StaticFileConfig",
    "VersioningStrategy",
    "WebConfig",
    "WebProviderConfig",
]

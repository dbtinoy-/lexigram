"""Web security configuration facade.

Re-exports every public name so that
``from lexigram.web.security.config import X`` continues to work unchanged.
"""

from lexigram.web.security.config.cors import CORSConfig as CORSConfig
from lexigram.web.security.config.csp import CSPConfig as CSPConfig
from lexigram.web.security.config.csrf import CSRFConfig as CSRFConfig
from lexigram.web.security.config.headers import (
    CrossOriginConfig as CrossOriginConfig,
)
from lexigram.web.security.config.headers import (
    HSTSConfig as HSTSConfig,
)
from lexigram.web.security.config.headers import (
    SecurityHeadersConfig as SecurityHeadersConfig,
)
from lexigram.web.security.config.top_level import SecurityConfig as SecurityConfig

__all__ = [
    "CORSConfig",
    "CSPConfig",
    "CSRFConfig",
    "CrossOriginConfig",
    "HSTSConfig",
    "SecurityConfig",
    "SecurityHeadersConfig",
]

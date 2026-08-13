"""Content Security Policy package for lexigram-web."""

from __future__ import annotations

from lexigram.web.security.config import CSPConfig
from lexigram.web.security.csp.builder import CSPPolicy

__all__ = ["CSPConfig", "CSPPolicy"]

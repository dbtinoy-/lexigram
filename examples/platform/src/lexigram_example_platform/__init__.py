"""lexigram-example-platform — multi-tenant SaaS reference application.

Demonstrates:
- Multi-tenant lifecycle management (lexigram domain aggregates)
- RBAC via a permission matrix (no if/elif chains)
- Feature flag integration (lexigram-features LocalProvider + FlagManager)
- Domain event publication via EventBusProtocol
- Result[T, E] pattern throughout all service use-cases
- Constructor injection for all service dependencies

See README.md for the full architecture walkthrough.
"""

from __future__ import annotations

from lexigram_example_platform.config import PlatformConfig
from lexigram_example_platform.module import PlatformModule

__all__ = [
    "PlatformConfig",
    "PlatformModule",
]

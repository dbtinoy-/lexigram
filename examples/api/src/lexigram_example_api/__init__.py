"""Lexigram Example API — reference application.

Demonstrates production-quality usage of the Lexigram Framework:
- Contract-based repositories (Protocol interfaces + in-memory implementations)
- Result[T, E] for all domain operations
- Constructor dependency injection via the DI container
- Domain events published via EventBusProtocol
- JWT authentication via lexigram-auth
- Structured logging via lexigram.logging
"""

from __future__ import annotations

"""Framework integrations: authentication, debugging, GraphQL, rate limiting."""

from __future__ import annotations

from lexigram.web.integrations.auth import AuthIntegration
from lexigram.web.integrations.cache import CacheIntegration
from lexigram.web.integrations.debug import DebugIntegration
from lexigram.web.integrations.graphql import GraphQLIntegration
from lexigram.web.integrations.rate_limit import RateLimitIntegration
from lexigram.web.integrations.setup import lifespan
from lexigram.web.integrations.sql import SQLIntegration
from lexigram.web.integrations.throttle import RateLimitModule, throttle

__all__ = [
    "AuthIntegration",
    "CacheIntegration",
    "DebugIntegration",
    "GraphQLIntegration",
    "RateLimitIntegration",
    "RateLimitModule",
    "SQLIntegration",
    "lifespan",
    "throttle",
]

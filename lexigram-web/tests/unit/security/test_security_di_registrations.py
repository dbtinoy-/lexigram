"""Tests for HTTP security DI registrations in WebProvider."""

from __future__ import annotations

import pytest

from lexigram.web.security.config import CORSConfig, CSRFConfig, SecurityConfig
from lexigram.web.security.cors.middleware import CORSMiddlewareFactory
from lexigram.web.security.csrf.protection import CSRFProtection


@pytest.mark.asyncio
async def test_web_provider_registers_http_security_configs(test_bed) -> None:
    """WebProvider should register its HTTP security config objects in DI."""
    from lexigram.web.di.provider import WebProvider

    provider = await test_bed.resolve(WebProvider)

    resolved_security = await test_bed.resolve(SecurityConfig)
    resolved_cors = await test_bed.resolve(CORSConfig)
    resolved_csrf = await test_bed.resolve(CSRFConfig)

    assert resolved_security is provider.web_config.security
    assert resolved_cors is provider.web_config.cors
    assert resolved_csrf is provider.web_config.security.csrf


@pytest.mark.asyncio
async def test_web_provider_registers_http_security_services(test_bed) -> None:
    """WebProvider should register HTTP security helper services in DI."""
    factory = await test_bed.resolve(CORSMiddlewareFactory)
    protection = await test_bed.resolve(CSRFProtection)

    assert isinstance(factory, CORSMiddlewareFactory)
    assert isinstance(protection, CSRFProtection)
    assert isinstance(protection.config, CSRFConfig)

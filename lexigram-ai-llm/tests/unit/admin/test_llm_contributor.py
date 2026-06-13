"""Unit tests for LlmAdminContributor widget rendering."""

from __future__ import annotations

from typing import Any

import pytest

from lexigram.ai.llm.admin.contributor import LlmAdminContributor
from lexigram.ai.llm.routing import InferenceError
from lexigram.contracts.admin.errors import (
    HealthCheckNotFoundError,
    WidgetNotFoundError,
)
from lexigram.contracts.admin.health_payload import HealthCheckPayload
from lexigram.contracts.admin.types import WidgetParams, WidgetViewModel
from lexigram.contracts.ai.routing import LLMRouterProtocol
from lexigram.contracts.core.health import HealthStatus
from lexigram.result import Err, Ok, Result


class FakeRouter:
    """Fake LLMRouterProtocol with a configurable health_probe outcome."""

    def __init__(
        self,
        *,
        healthy: bool,
    ) -> None:
        if healthy:
            self._outcome: Result[Any, InferenceError] = Ok(object())
        else:
            self._outcome = Err(
                InferenceError(
                    message="no healthy provider",
                    providers_tried=["fake"],
                    last_status_code=503,
                )
            )

    async def health_probe(self) -> Result[Any, InferenceError]:
        """Return the configured outcome."""
        return self._outcome


class FakeContainer:
    """Minimal container fake that resolves LLMRouterProtocol."""

    def __init__(self, router: FakeRouter) -> None:
        self._router = router

    async def resolve(self, service_type: type) -> Any:
        """Resolve a service by type."""
        if service_type is LLMRouterProtocol:
            return self._router
        raise AssertionError(f"unexpected protocol: {service_type}")


class TestLlmAdminContributor:
    """Tests for LlmAdminContributor widget rendering."""

    @pytest.fixture
    def contributor(self) -> LlmAdminContributor:
        """Create a fresh contributor instance."""
        return LlmAdminContributor()

    @pytest.mark.asyncio
    async def test_render_widget_token_usage(
        self, contributor: LlmAdminContributor
    ) -> None:
        """Test rendering token_usage widget returns Ok with WidgetViewModel."""
        result = await contributor.render_widget("token_usage", WidgetParams())
        assert result.is_ok()
        vm = result.unwrap()
        assert isinstance(vm, WidgetViewModel)

    @pytest.mark.asyncio
    async def test_unknown_widget_returns_not_found(
        self, contributor: LlmAdminContributor
    ) -> None:
        """Test that unknown widget names return WidgetNotFoundError."""
        result = await contributor.render_widget("nonexistent", WidgetParams())
        assert result.is_err()
        assert isinstance(result.unwrap_err(), WidgetNotFoundError)

    def test_get_dashboard_widgets_returns_three(
        self, contributor: LlmAdminContributor
    ) -> None:
        """Test that exactly three dashboard widgets are registered."""
        widgets = contributor.get_dashboard_widgets()
        assert len(widgets) == 3
        widget_names = {w.name for w in widgets}
        assert widget_names == {"token_usage", "provider_status", "error_rate"}

    @pytest.mark.asyncio
    async def test_render_health_check_returns_healthy_when_all_providers_healthy(
        self,
    ) -> None:
        """One enabled provider with a healthy client -> overall HEALTHY."""
        contributor = LlmAdminContributor()
        await contributor.on_admin_boot(FakeContainer(FakeRouter(healthy=True)))

        result = await contributor.render_health_check("provider")

        assert result.is_ok()
        payload = result.unwrap()
        assert isinstance(payload, HealthCheckPayload)
        assert payload.status == HealthStatus.HEALTHY
        assert payload.component == "LLM Provider"

    @pytest.mark.asyncio
    async def test_render_health_check_returns_healthy_when_at_least_one_provider_healthy(
        self,
    ) -> None:
        """health_probe is 'at least one healthy' — one healthy provider
        keeps the subsystem HEALTHY even if another provider fails."""
        contributor = LlmAdminContributor()
        await contributor.on_admin_boot(FakeContainer(FakeRouter(healthy=True)))

        result = await contributor.render_health_check("provider")

        assert result.is_ok()
        payload = result.unwrap()
        assert payload.status == HealthStatus.HEALTHY

    @pytest.mark.asyncio
    async def test_render_health_check_returns_unhealthy_when_no_provider_healthy(
        self,
    ) -> None:
        """No enabled provider passes its health check -> overall UNHEALTHY
        with 'no healthy provider' detail."""
        contributor = LlmAdminContributor()
        await contributor.on_admin_boot(FakeContainer(FakeRouter(healthy=False)))

        result = await contributor.render_health_check("provider")

        assert result.is_ok()
        payload = result.unwrap()
        assert payload.status == HealthStatus.UNHEALTHY
        assert payload.component == "LLM Provider"
        assert payload.detail == "no healthy provider"

    @pytest.mark.asyncio
    async def test_render_health_check_returns_not_found_for_unknown_check_name(
        self,
    ) -> None:
        """Unknown check names return HealthCheckNotFoundError."""
        result = await LlmAdminContributor().render_health_check("something_else")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), HealthCheckNotFoundError)

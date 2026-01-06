"""Tests that render_widget accepts resolver= parameter (S4)."""

from __future__ import annotations

import inspect

from lexigram.contracts.admin.contributor import BaseAdminContributor
from lexigram.contracts.admin.protocols import AdminContributorProtocol
from lexigram.contracts.admin.types import WidgetParams


class FakeResolver:
    async def resolve(self, service_type: object, *, bypass_visibility: bool = False) -> object:
        raise RuntimeError("not expected to be called in this test")

    async def call(self, func: object, *args: object, **kwargs: object) -> object:
        raise RuntimeError("not expected to be called in this test")

    def create_scope(self) -> object:
        return None

    def has(self, service_type: object) -> bool:
        return False

    async def resolve_optional(self, service_type: object) -> object:
        return None

    async def resolve_all(self, service_type: object) -> list[object]:
        return []


class MinimalContributor(BaseAdminContributor):
    name = "minimal"
    display_name = "Minimal"


async def test_render_widget_accepts_resolver_kwarg() -> None:
    c = MinimalContributor()
    resolver = FakeResolver()
    result = await c.render_widget("no_widget", WidgetParams(), resolver=resolver)
    assert result.is_err()


async def test_render_widget_accepts_no_resolver() -> None:
    c = MinimalContributor()
    result = await c.render_widget("no_widget", WidgetParams())
    assert result.is_err()


async def test_render_widget_resolver_none_by_default() -> None:
    c = MinimalContributor()
    result = await c.render_widget("no_widget", WidgetParams(), resolver=None)
    assert result.is_err()


def test_admin_contributor_protocol_render_widget_has_resolver_param() -> None:
    sig = inspect.signature(AdminContributorProtocol.render_widget)
    assert "resolver" in sig.parameters, (
        "AdminContributorProtocol.render_widget must have resolver parameter"
    )

"""Tests for GraphQL web contributor integration."""

from __future__ import annotations

from pathlib import Path
import tomllib

import pytest

from lexigram.contracts.web import WebContributorProtocol


def test_graphql_web_contributor_matches_protocol() -> None:
    """GraphQLWebContributor must match WebContributorProtocol shape."""
    from lexigram.graphql.web.contributor import GraphQLWebContributor

    contributor = GraphQLWebContributor()
    assert isinstance(contributor, WebContributorProtocol)


def test_graphql_web_contributor_returns_graphql_controller() -> None:
    """GraphQLWebContributor.get_controllers() must return [GraphQLController]."""
    from lexigram.graphql.controllers.graphql import GraphQLController
    from lexigram.graphql.web.contributor import GraphQLWebContributor

    contributor = GraphQLWebContributor()
    controllers = contributor.get_controllers()

    assert controllers == [GraphQLController]


def test_graphql_web_contributor_returns_no_middleware() -> None:
    """GraphQLWebContributor.get_middleware() must return empty list."""
    from lexigram.graphql.web.contributor import GraphQLWebContributor

    contributor = GraphQLWebContributor()
    middleware = contributor.get_middleware()

    assert middleware == []


def test_pyproject_has_web_contributor_entry_point() -> None:
    """pyproject.toml must declare graphql web contributor entry point."""
    pyproject_path = (
        Path(__file__).parent.parent.parent / "pyproject.toml"
    )
    assert pyproject_path.exists(), f"pyproject.toml not found at {pyproject_path}"

    with open(pyproject_path, "rb") as f:
        pyproject = tomllib.load(f)

    entry_points = pyproject.get("project", {}).get("entry-points", {})
    web_contributors = entry_points.get("lexigram.web.contributors", {})

    assert "graphql" in web_contributors
    assert (
        web_contributors["graphql"]
        == "lexigram.graphql.web.contributor:GraphQLWebContributor"
    )


def test_graphql_integration_no_longer_has_discover_controller() -> None:
    """GraphQLIntegration must not have discover_controller method."""
    from lexigram.web.integrations.graphql import GraphQLIntegration

    assert not hasattr(GraphQLIntegration, "discover_controller")


@pytest.mark.asyncio
async def test_graphql_web_contributor_mount_to_app_is_noop() -> None:
    from starlette.applications import Starlette

    from lexigram.graphql.web.contributor import GraphQLWebContributor

    contributor = GraphQLWebContributor()
    app = Starlette()

    await contributor.mount_to_app(app, object())

    assert app.routes == []

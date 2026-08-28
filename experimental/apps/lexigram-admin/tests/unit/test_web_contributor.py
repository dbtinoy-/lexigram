from __future__ import annotations

from pathlib import Path
import tomllib
from unittest.mock import AsyncMock

import pytest
from starlette.applications import Starlette

from lexigram.contracts.web import WebContributorProtocol


class _Resolver:
    def __init__(self, admin_bundle: object) -> None:
        self.admin_bundle = admin_bundle
        self.calls: list[tuple[object, bool]] = []

    async def resolve(self, token: object, *, bypass_visibility: bool = False) -> object | None:
        self.calls.append((token, bypass_visibility))
        if token == "admin_bundle":
            return self.admin_bundle
        return None


class _MissingResolver:
    async def resolve(self, token: object, *, bypass_visibility: bool = False) -> object | None:  # noqa: ARG002
        from lexigram.contracts.exceptions import UnresolvableDependencyError

        raise UnresolvableDependencyError("admin bundle is not registered")


def test_admin_web_contributor_matches_protocol() -> None:
    from lexigram.admin.web import AdminWebContributor

    contributor = AdminWebContributor()

    assert isinstance(contributor, WebContributorProtocol)
    assert contributor.contributor_id == "admin"
    assert contributor.get_controllers() == []
    assert contributor.get_middleware() == []


@pytest.mark.asyncio
async def test_admin_web_contributor_delegates_to_admin_bundle() -> None:
    from lexigram.admin.web import AdminWebContributor

    admin_bundle = type("Bundle", (), {"mount_to_app": AsyncMock()})()
    resolver = _Resolver(admin_bundle=admin_bundle)
    contributor = AdminWebContributor()
    app = Starlette()

    await contributor.mount_to_app(app, resolver)

    assert ("admin_bundle", True) in resolver.calls
    admin_bundle.mount_to_app.assert_awaited_once_with(app, resolver)


@pytest.mark.asyncio
async def test_admin_web_contributor_skips_when_bundle_is_not_registered() -> None:
    from lexigram.admin.web import AdminWebContributor

    contributor = AdminWebContributor()
    await contributor.mount_to_app(Starlette(), _MissingResolver())


def test_admin_pyproject_declares_web_contributor_entry_point() -> None:
    pyproject_path = Path(__file__).resolve().parents[2] / "pyproject.toml"
    data = tomllib.loads(pyproject_path.read_text())

    assert (
        data["project"]["entry-points"]["lexigram.web.contributors"]["admin"]
        == "lexigram.admin.web.contributor:AdminWebContributor"
    )

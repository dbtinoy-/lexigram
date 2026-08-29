from __future__ import annotations

"""Scenario-specific app factories for cross-package integration tests.

Each factory creates a minimal Lexigram application configured for
a specific package composition scenario. Real infrastructure credentials
come from IntegrationTestConfig (environment variables / Docker Compose defaults).
The relay factories compose the real provider/module graph from installed
entry points with contract-level fakes injected through the container.

Usage::

    @pytest.fixture
    async def app(crud_app_factory):
        async with AppTestBed.from_factory(crud_app_factory) as bed:
            yield bed
"""

import os

import pytest  # noqa: F401  — re-exported for scenario fixtures
from starlette.middleware.base import BaseHTTPMiddleware


def _postgres_dsn() -> str:
    """Return the PostgreSQL DSN from the environment or Docker Compose default.

    Returns:
        A SQLAlchemy-compatible asyncpg DSN string.
    """
    return os.environ.get(
        "LEX_TEST_POSTGRES_DSN",
        "postgresql+asyncpg://lexigram:lexigram@localhost:15432/lexigram_test",
    )


def _redis_url() -> str:
    """Return the Redis URL from the environment or Docker Compose default.

    Returns:
        A Redis URL string targeting database 15 to avoid collisions.
    """
    return os.environ.get(
        "LEX_TEST_REDIS_URL",
        "redis://localhost:16379/15",
    )


# NOTE: These factory functions are stubs. Each scenario test should
# provide its own fixture that boots the relevant application stack.
# Uncomment and flesh out once the relevant packages are stable.

# @pytest.fixture
# def crud_app_factory():
#     """Minimal Web + SQL application for CRUD scenarios."""
#     def _factory():
#         pytest.skip("TODO: create_crud_app factory not yet implemented")
#     return _factory


# ---------------------------------------------------------------------------
# Relay system fixtures (integration plan: entry-point composition + boot)
# ---------------------------------------------------------------------------

RELAY_ENTRY_POINT_GROUPS = (
    "lexigram.providers",
    "lexigram.ai.modules",
    "lexigram.ai.subsystems",
    "lexigram.web.contributors",
    "lexigram.admin.contributors",
)
"""Entry-point groups the relay system registers against."""


@pytest.fixture
def relay_entry_points() -> dict[str, dict[str, object]]:
    """Load the relay entry-point groups from installed metadata.

    The snapshot fails on duplicate names within a group and never
    monkeypatches production imports.

    Returns:
        Group name to ``{entry name: loaded object}`` mapping.
    """
    import importlib.metadata

    by_group: dict[str, dict[str, object]] = {}
    for group in RELAY_ENTRY_POINT_GROUPS:
        loaded: dict[str, object] = {}
        for entry in importlib.metadata.entry_points(group=group):
            assert entry.name not in loaded, (
                f"duplicate entry point name {entry.name!r} in {group}"
            )
            loaded[entry.name] = entry.load()
        by_group[group] = loaded
    return by_group


@pytest.fixture
def relay_fakes():
    """Return a fresh bundle of relay fakes per test."""
    from tests.integration.scenarios.relay_fakes import RelayFakes

    return RelayFakes()


@pytest.fixture
async def relay_app_factory(relay_fakes):
    """Build a booted relay application composition.

    The factory composes the real web, http, admin, relay, relay-gateway,
    and governance modules and overrides external upstream, auth, billing,
    metrics, and persistence implementations through the container.

    Returns:
        An async callable returning a :class:`~relay_fakes.RelayAppHarness`.
    """

    async def _build():
        # Snapshot the import table before boot so the boot test can assert
        # that provider boot itself did not import optional LLM SDKs, even
        # when an earlier test in the session already imported them.
        import sys as _sys

        modules_before_boot = frozenset(_sys.modules)

        from lexigram.admin import AdminModule
        from lexigram.admin.config import AdminConfig
        from lexigram.ai.governance import GovernanceModule
        from lexigram.ai.governance.config import GovernanceConfig
        from lexigram.ai.relay import RelayModule
        from lexigram.ai.relay.gateway import RelayGatewayModule
        from lexigram.ai.relay.gateway.config import RelayGatewayConfig
        from lexigram.ai.relay.gateway.di.provider import RelayGatewayProvider
        from lexigram.app.base import Application
        from lexigram.contracts.ai.governance import (
            AIAuditStoreProtocol,
            RelayBillingProtocol,
            RelayUsageStoreProtocol,
        )
        from lexigram.contracts.ai.relay import (
            RelayConverterProtocol,
            RelayFormat,
            RelayGatewayProtocol,
        )
        from lexigram.contracts.ai.relay.gateway import RelayChannel
        from lexigram.contracts.ai.relay.operations import (
            RelayOperationsControlProtocol,
            RelayOperationsProtocol,
        )
        from lexigram.contracts.data import DatabaseProviderProtocol
        from lexigram.contracts.events.protocols import EventBusProtocol
        from lexigram.contracts.feature_flags.protocols import FlagManagerProtocol
        from lexigram.contracts.web import HTTPClientProtocol
        from lexigram.di.module import DynamicModule
        from lexigram.http import HTTPModule
        from lexigram.web import WebModule
        from lexigram.web.config import ServerConfig, WebConfig
        from lexigram.web.security.config import SecurityConfig
        from tests.integration.scenarios.relay_fakes import (
            RelayAppHarness,
            StubDatabaseProvider,
            StubFlagManager,
        )

        config = RelayGatewayConfig(
            require_auth=False,
            channels=(
                RelayChannel(
                    name="claude",
                    upstream_base_url="https://relay-upstream.invalid",
                    target_format=RelayFormat.CLAUDE,
                    models=("claude-sonnet-4",),
                ),
                RelayChannel(
                    name="claude-fast",
                    upstream_base_url="https://relay-upstream.invalid",
                    target_format=RelayFormat.CLAUDE,
                    models=("claude-3-5-haiku-20241022",),
                ),
            ),
            model_suffix={"claude-sonnet-4": "claude-3-5-sonnet-20241022"},
        )
        gateway_module = DynamicModule(
            module=RelayGatewayModule,
            providers=[
                RelayGatewayProvider(
                    config=config,
                    converter=relay_fakes.converter,
                    http_client=relay_fakes.http_client,
                    authorizer=relay_fakes.authorizer,
                    billing=relay_fakes.billing,
                    media_resolver=relay_fakes.media_resolver,
                    audit=relay_fakes.audit_store,
                )
            ],
            exports=[RelayGatewayProtocol],
        )
        app = Application(name="relay-scenario")
        app.add_modules(
            [
                WebModule.configure(
                    host="127.0.0.1",
                    web_config=WebConfig(
                        server=ServerConfig(host="127.0.0.1"),
                        security=SecurityConfig(enable_csrf=False),
                    ),
                ),
                HTTPModule.configure(),
                RelayModule.configure(),
                gateway_module,
                GovernanceModule.configure(GovernanceConfig(enabled=False)),
                AdminModule.stub(
                    AdminConfig.from_dict(
                        {"auth": {"security": {"setup_token": "test-setup-token"}}}
                    )
                ),
            ]
        )

        # Bind fakes the modules do not register before the app starts so
        # provider boot never touches real persistence or event systems.
        container = app.container
        container.singleton(RelayOperationsProtocol, relay_fakes.operations)
        container.singleton(
            RelayOperationsControlProtocol, relay_fakes.operations_control
        )
        container.singleton(RelayUsageStoreProtocol, relay_fakes.usage_store)
        container.singleton(EventBusProtocol, relay_fakes.event_bus)
        container.singleton(AIAuditStoreProtocol, relay_fakes.audit_store)
        container.singleton(FlagManagerProtocol, StubFlagManager())
        container.singleton(DatabaseProviderProtocol, StubDatabaseProvider())

        await app.start()

        # Relay routes derive the tenant from the authenticated user state.
        # No auth provider is composed in this scenario, so a minimal
        # Starlette middleware fabricates the normalized user dict.
        from lexigram.contracts.web import WebProviderProtocol

        web_provider = await container.resolve(WebProviderProtocol)
        starlette_app: Any = web_provider.starlette
        if starlette_app is not None:
            starlette_app.add_middleware(_TenantUserMiddleware)

        # Replace module-owned external bindings after boot: container
        # overrides win over the real HTTP client, billing policy, and
        # conversion engine.
        container.bind(HTTPClientProtocol, relay_fakes.http_client)
        container.bind(RelayBillingProtocol, relay_fakes.billing)
        container.bind(RelayConverterProtocol, relay_fakes.converter)

        return RelayAppHarness(
            app=app,
            fakes=relay_fakes,
            modules_before_boot=modules_before_boot,
        )

    return _build


@pytest.fixture
async def relay_app(relay_app_factory):
    """Yield one booted relay harness per test and stop it afterwards."""
    harness = await relay_app_factory()
    try:
        yield harness
    finally:
        await harness.app.stop()


class _TenantUserMiddleware(BaseHTTPMiddleware):
    """Starlette middleware fabricating a normalized user on every request.

    The relay gateway derives ``request.state.user["tenant_id"]`` from
    the auth middleware; none is composed in this scenario, so this
    middleware synthesizes the user dict for the relay routes.
    """

    async def dispatch(self, request: Any, call_next: Any) -> Any:
        """Attach the fabricated user and continue the chain."""
        request.state.user = {"tenant_id": "tenant-1", "user_id": "user-1"}
        return await call_next(request)

"""Tests for the admin session-signing secret (P0: F1)."""

from __future__ import annotations

from types import SimpleNamespace

from starlette.middleware.sessions import SessionMiddleware


class TestAdminRouterSessionSecret:
    def test_mount_signs_with_auth_session_secret(self) -> None:
        from lexigram.admin.config import AdminAuthConfig, AdminConfig
        from lexigram.admin.core.routing import AdminRouter

        config = AdminConfig(
            auth=AdminAuthConfig(
                env="production",
                session_secret="x" * 64,
            ),
        )
        router = AdminRouter(config=config)
        app = SimpleNamespace(routes=[])

        admin_app = router.mount(app)

        assert admin_app is not None
        session_middleware = [
            m
            for m in admin_app.user_middleware
            if m.cls is SessionMiddleware
        ]
        assert len(session_middleware) == 1
        assert session_middleware[0].kwargs["secret_key"] == "x" * 64
        assert session_middleware[0].kwargs["https_only"] is True
        assert session_middleware[0].kwargs["same_site"] == "strict"

    def test_mount_never_uses_hardcoded_dev_literal(self) -> None:
        from lexigram.admin.config import AdminAuthConfig, AdminConfig
        from lexigram.admin.core.routing import AdminRouter

        config = AdminConfig(
            auth=AdminAuthConfig(session_secret="a-strong-secret-abcdefgh"),
        )
        router = AdminRouter(config=config)
        app = SimpleNamespace(routes=[])

        admin_app = router.mount(app)

        session_middleware = [
            m
            for m in admin_app.user_middleware
            if m.cls is SessionMiddleware
        ]
        options = session_middleware[0].kwargs
        assert options["secret_key"] == "a-strong-secret-abcdefgh"
        assert "dev-secret-key-change-in-production" not in str(options)

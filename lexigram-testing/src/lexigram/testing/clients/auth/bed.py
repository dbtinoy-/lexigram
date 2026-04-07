"""Test bed for lexigram-auth testing."""

from __future__ import annotations

from typing import Any, Self

from lexigram.auth.di import AuthenticationProvider
from lexigram.auth.storage.token_store import InMemoryUserStore, UserStoreProtocol
from lexigram.testing import TestEnvironment
from lexigram.testing.clients.auth.types import AuthTestUser


class AuthTestBed(TestEnvironment):
    """Test bed for lexigram-auth testing.

    Provides a complete testing environment with mock auth providers,
    user stores, and token managers.

    Example:
        >>> async with AuthTestBed() as bed:
        ...     client = AuthTestClient(bed)
        ...     # Use client for testing
    """

    def __init__(self, **kwargs: Any) -> None:
        """Initialize the auth test bed."""
        super().__init__(**kwargs)
        self._auth_provider: AuthenticationProvider | None = None
        self._user_store: UserStoreProtocol | None = None

    async def setup(self) -> TestEnvironment:
        """Setup the test environment with auth providers."""
        # First call parent setup
        app = await super().setup()

        # Then setup auth-specific providers
        await self.setup_providers()

        return app

    async def setup_providers(self) -> None:
        """Set up auth-related providers."""
        # Set up user store
        self._user_store = InMemoryUserStore()
        assert self.container is not None
        self.container.singleton(UserStoreProtocol, lambda: self._user_store)

        # Set up auth provider
        self._auth_provider = AuthenticationProvider(  # type: ignore[call-arg]
            secret_key="test_secret_key_for_testing_only",
            user_store=self._user_store,
        )
        assert self.container is not None
        self.container.singleton(AuthenticationProvider, lambda: self._auth_provider)

        # Register the auth provider
        await self._auth_provider.register(self.container)

    async def teardown_providers(self) -> None:
        """Clean up auth-related providers."""
        if self._auth_provider:
            # Clear users from store
            if self._user_store:
                users = await self._user_store.list_users()
                for user in users:
                    await self._user_store.delete_user(user.user_id)

        await super().teardown_providers()  # type: ignore[misc]

    @property
    def auth_provider(self) -> AuthenticationProvider:
        """Get the auth provider."""
        from typing import cast

        return cast("AuthenticationProvider", self._auth_provider)

    @property
    def user_store(self) -> UserStoreProtocol:
        """Get the user store."""
        from typing import cast

        return cast("UserStoreProtocol", self._user_store)

    async def create_test_user(
        self,
        username: str,
        email: str,
        password: str = "password123",  # noqa: S107  # intentional default for test users
        **kwargs: Any,
    ) -> AuthTestUser:
        """Create a test user."""
        return await AuthTestUser.create(username, email, password, **kwargs)

    def create_test_token(self, user: AuthTestUser, **kwargs: Any) -> Any:
        """Create a test token (synchronous helper)."""
        from lexigram.testing.clients.auth.types import AuthTestToken as _AuthTestToken

        return _AuthTestToken.create(user, **kwargs)

    async def __aenter__(self) -> Self:
        """Async context manager entry."""
        await self.setup()
        return self

    async def __aexit__(
        self,
        exc_type: type[BaseException] | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        """Async context manager exit."""
        await self.teardown()  # type: ignore[misc,func-returns-value]

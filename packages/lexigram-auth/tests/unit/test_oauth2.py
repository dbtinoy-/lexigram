"""Tests for OAuth2 authentication functionality"""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from lexigram.auth.authn.oauth2 import (
    LexigramConnectResponse,
    LexigramConnectSession,
    OAuth2AuthProvider,
    OAuth2Manager,
    OAuth2IdentityProvider,
    OAuth2UserInfo,
)


class TestOAuth2IdentityProvider:
    """Test OAuth2 provider configuration"""

    def test_provider_creation(self):
        """Test OAuth2 provider creation"""
        provider = OAuth2IdentityProvider(
            name="google",
            client_id="test_client_id",
            client_secret="test_client_secret",
            authorize_url="https://accounts.google.com/oauth/authorize",
            access_token_url="https://oauth2.googleapis.com/token",
            userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
            scope="openid email profile",
        )

        assert provider.name == "google"
        assert provider.client_id == "test_client_id"
        assert provider.client_secret == "test_client_secret"
        assert provider.authorize_url == "https://accounts.google.com/oauth/authorize"
        assert provider.access_token_url == "https://oauth2.googleapis.com/token"
        assert (
            provider.userinfo_url == "https://openidconnect.googleapis.com/v1/userinfo"
        )
        assert provider.scope == "openid email profile"


class TestLexigramConnectSession:
    """Test LexigramConnect session adapter"""

    def setup_method(self):
        """Setup test method"""
        self.mock_http_client = AsyncMock()
        self.session = LexigramConnectSession(self.mock_http_client)

    @pytest.mark.asyncio
    async def test_request_get(self):
        """Test GET request"""
        mock_response = MagicMock()
        mock_response.status = 200
        mock_response.headers = {"content-type": "application/json"}
        self.mock_http_client.get.return_value = mock_response

        response = await self.session.get("https://example.com/api")
        assert isinstance(response, LexigramConnectResponse)
        assert response.status_code == 200

    @pytest.mark.asyncio
    async def test_request_post(self):
        """Test POST request"""
        mock_response = MagicMock()
        mock_response.status = 201
        self.mock_http_client.post.return_value = mock_response

        response = await self.session.post(
            "https://example.com/api", data={"key": "value"},
        )
        assert isinstance(response, LexigramConnectResponse)
        assert response.status_code == 201


class TestLexigramConnectResponse:
    """Test LexigramConnect response adapter"""

    def setup_method(self):
        """Setup test method"""
        self.mock_response = MagicMock()
        self.mock_response.status = 200
        self.mock_response.headers = {"content-type": "application/json"}
        self.response = LexigramConnectResponse(self.mock_response)

    def test_status_code(self):
        """Test status code property"""
        assert self.response.status_code == 200

    def test_headers(self):
        """Test headers property"""
        assert self.response.headers == {"content-type": "application/json"}

    @pytest.mark.asyncio
    async def test_json(self):
        """Test JSON parsing"""

        async def mock_json():
            return {"user": "test"}

        self.mock_response.json = mock_json
        result = await self.response.json()
        assert result == {"user": "test"}

    @pytest.mark.asyncio
    async def test_text(self):
        """Test text content"""

        async def mock_text():
            return "Hello World"

        self.mock_response.text = mock_text
        result = await self.response.text()
        assert result == "Hello World"

    def test_raise_for_status(self):
        """Test raise for status"""
        self.response.raise_for_status()
        # Should not raise for 200 status


class TestOAuth2Manager:
    """Test OAuth2 manager"""

    @pytest.fixture
    def providers(self):
        return {
            "google": OAuth2IdentityProvider(
                name="google",
                client_id="test_client_id",
                client_secret="test_client_secret",
                authorize_url="https://accounts.google.com/oauth/authorize",
                access_token_url="https://oauth2.googleapis.com/token",
                userinfo_url="https://openidconnect.googleapis.com/v1/userinfo",
            ),
        }

    @pytest.mark.asyncio
    async def test_get_authorization_url(self, mocker, providers):
        """Test authorization URL generation and PKCE verifier"""
        mocker.patch("lexigram.auth.authn.oauth2.HAS_AUTHLIB", True)
        mock_client_class = mocker.MagicMock()
        mocker.patch("lexigram.auth.authn.oauth2.AsyncOAuth2Client", mock_client_class)

        mock_client = MagicMock()
        # emulate authlib returning (url, state)
        mock_client.create_authorization_url.return_value = (
            "https://example.com/auth",
            "state123",
        )
        mock_client_class.return_value = mock_client

        manager = OAuth2Manager(providers)
        url, code_verifier, state = await manager.get_authorization_url("google", "test_state")
        assert url == "https://example.com/auth"
        assert isinstance(code_verifier, str) and len(code_verifier) > 0
        assert state == "test_state"
        mock_client.create_authorization_url.assert_called_once()

    @pytest.mark.asyncio
    async def test_get_authorization_url_unknown_provider(self, providers):
        """Test authorization URL with unknown provider"""
        with patch("lexigram.auth.authn.oauth2.HAS_AUTHLIB", True):
            manager = OAuth2Manager(providers)
            with pytest.raises(
                ValueError, match="OAuth2 provider 'unknown' not configured",
            ):
                await manager.get_authorization_url("unknown")

    @pytest.mark.asyncio
    async def test_exchange_code_for_token(self, mocker, providers):
        """Test token exchange"""
        mocker.patch("lexigram.auth.authn.oauth2.HAS_AUTHLIB", True)
        mock_client_class = mocker.MagicMock()
        mocker.patch("lexigram.auth.authn.oauth2.AsyncOAuth2Client", mock_client_class)

        mock_client = MagicMock()
        mock_client.fetch_token = AsyncMock(
            return_value={"access_token": "token123", "token_type": "Bearer"},
        )
        mock_client_class.return_value = mock_client

        manager = OAuth2Manager(providers)
        # PKCE is required by default; always pass code_verifier
        token = await manager.exchange_code_for_token("google", "auth_code", code_verifier="verifier123")
        assert token == {"access_token": "token123", "token_type": "Bearer"}

        # Test PKCE verifier is forwarded
        _ = await manager.exchange_code_for_token(
            "google", "auth_code", code_verifier="verifier123",
        )
        mock_client.fetch_token.assert_called_with(
            providers["google"].access_token_url,
            code="auth_code",
            code_verifier="verifier123",
        )

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_pkce_enforcement(self, providers):
        """Test that PKCE is enforced when require_pkce=True (default)."""
        from lexigram.auth.exceptions import OAuth2Error

        manager = OAuth2Manager(providers)
        with pytest.raises(OAuth2Error, match="PKCE code_verifier is required"):
            await manager.exchange_code_for_token("google", "auth_code")

    @pytest.mark.asyncio
    async def test_exchange_code_for_token_error(self, mocker, providers):
        """Test token exchange with error"""
        mocker.patch("lexigram.auth.authn.oauth2.HAS_AUTHLIB", True)
        mock_client_class = mocker.MagicMock()
        mocker.patch("lexigram.auth.authn.oauth2.AsyncOAuth2Client", mock_client_class)

        from lexigram.auth.authn.oauth2 import OAuthError

        mock_client = MagicMock()
        mock_client.fetch_token = AsyncMock(side_effect=OAuthError("Invalid code"))
        mock_client_class.return_value = mock_client

        manager = OAuth2Manager(providers)
        with pytest.raises(ValueError, match="OAuth2 token exchange failed"):
            # PKCE is required; pass code_verifier to reach the exchange logic
            await manager.exchange_code_for_token("google", "invalid_code", code_verifier="verifier123")

    @pytest.mark.asyncio
    async def test_get_user_info(self, mocker, providers):
        """Test user info retrieval"""
        mocker.patch("lexigram.auth.authn.oauth2.HAS_AUTHLIB", True)
        mock_client_class = mocker.MagicMock()
        mocker.patch("lexigram.auth.authn.oauth2.AsyncOAuth2Client", mock_client_class)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "sub": "user123",
            "email": "user@example.com",
        }
        mock_client.get = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client

        manager = OAuth2Manager(providers)
        user_info = await manager.get_user_info("google", {"access_token": "token123"})
        assert user_info == {"sub": "user123", "email": "user@example.com"}

    @pytest.mark.asyncio
    async def test_get_user_info_error(self, mocker, providers):
        """Test user info retrieval with error"""
        mocker.patch("lexigram.auth.authn.oauth2.HAS_AUTHLIB", True)
        mock_client_class = mocker.MagicMock()
        mocker.patch("lexigram.auth.authn.oauth2.AsyncOAuth2Client", mock_client_class)

        mock_client = MagicMock()
        mock_client.get = AsyncMock(side_effect=Exception("Network error"))
        mock_client_class.return_value = mock_client

        manager = OAuth2Manager(providers)
        with pytest.raises(ValueError, match="Failed to get user info"):
            await manager.get_user_info("google", {"access_token": "token123"})

    def test_manager_without_authlib(self):
        """Test manager creation when authlib is not available"""
        with patch("lexigram.auth.authn.oauth2.HAS_AUTHLIB", False):
            # Constructing the manager should not raise; it will be created in a
            # test-friendly no-op mode where network ops raise at call-time.
            manager = OAuth2Manager({})
            assert hasattr(manager, "_available") and manager._available is False

    @patch("lexigram.auth.authn.oauth2.HAS_AUTHLIB", True)
    @pytest.mark.asyncio
    async def test_manager_with_http_client(self, providers):
        """Test manager with custom HTTP client"""
        mock_http_client = AsyncMock()
        manager = OAuth2Manager(providers, http_client=mock_http_client)

        # Test that http_client is stored
        assert manager._http_client == mock_http_client


class TestOAuth2UserInfo:
    """Test OAuth2 user info dataclass"""

    def test_user_info_creation(self):
        """Test OAuth2UserInfo creation"""
        user_info = OAuth2UserInfo(
            provider="google",
            provider_user_id="user123",
            email="user@example.com",
            email_verified=True,
            username="testuser",
            name="Test User",
            avatar_url="https://example.com/avatar.jpg",
            raw_data={"sub": "user123", "email": "user@example.com"},
        )

        assert user_info.provider == "google"
        assert user_info.provider_user_id == "user123"
        assert user_info.email == "user@example.com"
        assert user_info.email_verified is True
        assert user_info.username == "testuser"
        assert user_info.name == "Test User"
        assert user_info.avatar_url == "https://example.com/avatar.jpg"
        assert user_info.raw_data == {"sub": "user123", "email": "user@example.com"}

    def test_user_info_defaults(self):
        """Test OAuth2UserInfo with minimal data"""
        user_info = OAuth2UserInfo(
            provider="github",
            provider_user_id="456",
        )

        assert user_info.provider == "github"
        assert user_info.provider_user_id == "456"
        assert user_info.email is None
        assert user_info.email_verified is False
        assert user_info.username is None
        assert user_info.name is None
        assert user_info.avatar_url is None
        assert user_info.raw_data is None


class TestOAuth2AuthProvider:
    """Test OAuth2 authentication provider"""

    @pytest.fixture
    def mock_oauth2_manager(self):
        """Mock OAuth2 manager"""
        manager = AsyncMock()
        manager.exchange_code_for_token.return_value = {
            "access_token": "token123",
            "token_type": "Bearer",
        }
        manager.get_user_info.return_value = {
            "id": "user123",
            "email": "user@example.com",
            "email_verified": True,
            "login": "testuser",
            "name": "Test User",
            "avatar_url": "https://example.com/avatar.jpg",
        }
        return manager

    @pytest.fixture
    def mock_user_store(self):
        """Mock user store"""
        store = AsyncMock()
        store.get_user_by_email.return_value = None
        store.create_user.return_value = MagicMock(
            user_id="user123",
            name="testuser",
            email="user@example.com",
        )
        return store

    @pytest.fixture
    def oauth2_auth_provider(self, mock_oauth2_manager, mock_user_store):
        """OAuth2 auth provider fixture"""
        return OAuth2AuthProvider(
            oauth2_manager=mock_oauth2_manager,
            user_store=mock_user_store,
            oauth_identity_store=None,
        )

    @pytest.mark.asyncio
    async def test_authenticate_with_oauth2_new_user(
        self, oauth2_auth_provider, mock_oauth2_manager, mock_user_store,
    ):
        """Test OAuth2 authentication with new user provisioning"""
        user = await oauth2_auth_provider.authenticate_with_oauth2(
            "google", "auth_code",
        )

        # Verify token exchange was called
        mock_oauth2_manager.exchange_code_for_token.assert_called_once_with(
            "google", "auth_code",
        )

        # Verify user info was retrieved
        mock_oauth2_manager.get_user_info.assert_called_once_with(
            "google",
            {
                "access_token": "token123",
                "token_type": "Bearer",
            },
        )

        # Verify user was created
        mock_user_store.create_user.assert_called_once_with(
            name="testuser",
            email="user@example.com",
            hashed_password=None,
            roles=["user"],
            is_verified=True,
            profile={
                "name": "Test User",
                "avatar_url": "https://example.com/avatar.jpg",
                "oauth_provider": "google",
            },
        )

        assert user is not None

    @pytest.mark.asyncio
    async def test_authenticate_with_oauth2_existing_user(
        self, oauth2_auth_provider, mock_user_store,
    ):
        """Test OAuth2 authentication with existing user"""
        # Mock existing user
        existing_user = MagicMock()
        mock_user_store.get_user_by_email.return_value = existing_user

        user = await oauth2_auth_provider.authenticate_with_oauth2(
            "google", "auth_code",
        )

        # Should return existing user without creating new one
        assert user == existing_user
        mock_user_store.get_user_by_email.assert_called_once()
        mock_user_store.create_user.assert_not_called()

    @pytest.mark.asyncio
    async def test_authenticate_with_oauth2_with_identity_store(
        self, mock_oauth2_manager, mock_user_store,
    ):
        """Test OAuth2 authentication with identity store"""
        # Mock identity store
        identity_store = AsyncMock()
        identity_store.get_oauth_identity.return_value = None  # No existing identity
        identity_store.create_oauth_identity.return_value = MagicMock()

        provider = OAuth2AuthProvider(
            oauth2_manager=mock_oauth2_manager,
            user_store=mock_user_store,
            oauth_identity_store=identity_store,
        )

        await provider.authenticate_with_oauth2("google", "auth_code")

        # Should create OAuth identity
        identity_store.create_oauth_identity.assert_called_once_with(
            user_id="user123",
            provider="google",
            provider_user_id="user123",
        )

    @pytest.mark.asyncio
    async def test_authenticate_with_oauth2_existing_identity(
        self, mock_oauth2_manager, mock_user_store,
    ):
        """Test OAuth2 authentication with existing identity"""
        # Mock existing identity and user
        existing_user = MagicMock()
        identity_store = AsyncMock()
        identity_store.get_oauth_identity.return_value = MagicMock(
            user_id="existing_user_id",
        )
        mock_user_store.get_user_by_id.return_value = existing_user

        provider = OAuth2AuthProvider(
            oauth2_manager=mock_oauth2_manager,
            user_store=mock_user_store,
            oauth_identity_store=identity_store,
        )

        user = await provider.authenticate_with_oauth2("google", "auth_code")

        # Should find existing user by identity
        assert user == existing_user
        mock_user_store.create_user.assert_not_called()

    @pytest.fixture(params=["absent", "false"])
    def mock_oauth2_manager_unverified(self, request):
        """Mock OAuth2 manager without a verified-email claim"""
        manager = AsyncMock()
        manager.exchange_code_for_token.return_value = {
            "access_token": "token123",
            "token_type": "Bearer",
        }
        info = {
            "id": "user123",
            "email": "user@example.com",
            "login": "testuser",
            "name": "Test User",
        }
        if request.param == "false":
            info["email_verified"] = False
        manager.get_user_info.return_value = info
        return manager

    @pytest.mark.asyncio
    async def test_unverified_claim_never_binds_by_email(
        self, mock_oauth2_manager_unverified, mock_user_store,
    ):
        """Unverified email never takes over the existing-email account"""
        existing_user = MagicMock()
        mock_user_store.get_user_by_email.return_value = existing_user

        provider = OAuth2AuthProvider(
            oauth2_manager=mock_oauth2_manager_unverified,
            user_store=mock_user_store,
            oauth_identity_store=None,
        )
        user = await provider.authenticate_with_oauth2("google", "auth_code")

        assert user is not None
        assert user != existing_user
        mock_user_store.get_user_by_email.assert_not_called()
        mock_user_store.create_user.assert_called_once_with(
            name="testuser",
            email="user@example.com",
            hashed_password=None,
            roles=["user"],
            is_verified=False,
            profile={
                "name": "Test User",
                "avatar_url": None,
                "oauth_provider": "google",
            },
        )

    @pytest.mark.asyncio
    async def test_unverified_email_still_binds_by_identity(
        self, mock_oauth2_manager_unverified, mock_user_store,
    ):
        """Unverified email falls through to the identity match"""
        existing_user = MagicMock()
        identity_store = AsyncMock()
        identity_store.get_oauth_identity.return_value = MagicMock(
            user_id="existing_user_id",
        )
        mock_user_store.get_user_by_id.return_value = existing_user

        provider = OAuth2AuthProvider(
            oauth2_manager=mock_oauth2_manager_unverified,
            user_store=mock_user_store,
            oauth_identity_store=identity_store,
        )
        user = await provider.authenticate_with_oauth2("google", "auth_code")

        assert user == existing_user
        mock_user_store.get_user_by_email.assert_not_called()
        mock_user_store.create_user.assert_not_called()

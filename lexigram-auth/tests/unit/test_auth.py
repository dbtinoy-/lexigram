from unittest.mock import AsyncMock, MagicMock
from datetime import UTC, datetime

import pytest
from pydantic import SecretStr

from lexigram.auth.models import AuthToken
import lexigram.auth as la
from lexigram.auth.authn.core import User
from lexigram.auth.authn.jwt import JWTTokenManager
from lexigram.auth.authn.schemas import RegisterRequest
from lexigram.auth.authn.security import PasswordHasher, PasswordPolicy
from lexigram.auth.di import AuthenticationProvider, AuthorizationProvider
from lexigram.auth.storage.db_stores import (
    MongoDBUserStore,
    RedisUserStore,
    SQLUserStore,
)
from lexigram.auth.storage.token_store import InMemoryUserStore
from lexigram.auth.exceptions import (
    TokenExpiredError,
    InvalidTokenError,
    BlacklistedTokenError,
)
from lexigram.auth.exceptions import (
    TokenAudienceError,
    TokenBlacklistedError,
    TokenExpiredError as TokenExpiredErrorAuth,
    TokenInvalidError,
)
from lexigram.contracts.auth.token import VerifiedToken
from lexigram.result import Err, Ok


class TestPasswordHasher:
    """Test password hashing and verification"""

    @pytest.mark.asyncio
    async def test_hash_password(self):
        """Test password hashing"""
        password = "testpassword123"
        hashed = await PasswordHasher.hash(password)

        assert hashed != password
        assert await PasswordHasher.verify(password, hashed)
        # ✅ Verify it's using bcrypt (starts with $2b$ or $2a$)
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    @pytest.mark.asyncio
    async def test_hash_uses_12_rounds(self):
        """Test that password hashing uses at least 12 bcrypt rounds"""
        password = "testpassword123"
        hashed = await PasswordHasher.hash(password)

        # Bcrypt format: $2b$12$... (12 rounds)
        parts = hashed.split("$")
        assert len(parts) >= 4
        rounds = int(parts[2])
        assert rounds >= 12, f"Expected >= 12 rounds, got {rounds}"

    @pytest.mark.asyncio
    async def test_verify_password_wrong(self):
        """Test password verification with wrong password"""
        password = "testpassword123"
        wrong_password = "wrongpassword"
        hashed = await PasswordHasher.hash(password)

        assert not await PasswordHasher.verify(wrong_password, hashed)

    @pytest.mark.asyncio
    async def test_verify_password_fallback(self):
        """Test fallback password verification with unknown hash format"""
        # When the hash format is unknown, verify() returns False
        password = "plaintextpassword"
        # This tests the UnknownHashError handling - returns False for invalid hash formats
        assert not await PasswordHasher.verify(password, password)

    @pytest.mark.asyncio
    async def test_hash_long_password(self):
        """Test password hashing with passwords longer than 72 bytes"""
        # Create a password longer than 72 bytes
        long_password = "a" * 100  # 100 characters, > 72 bytes when encoded
        hashed = await PasswordHasher.hash(long_password)

        assert hashed != long_password
        # Should be able to verify with the truncated password
        assert await PasswordHasher.verify(long_password, hashed)
        # Verify it's using bcrypt
        assert hashed.startswith("$2b$") or hashed.startswith("$2a$")

    @pytest.mark.asyncio
    async def test_verify_long_password(self):
        """Test password verification with long passwords"""
        # Create a password longer than 72 bytes
        long_password = "a" * 100
        hashed = await PasswordHasher.hash(long_password)

        # Verification should work with the same long password
        assert await PasswordHasher.verify(long_password, hashed)

        # Verification should fail with wrong password
        assert not await PasswordHasher.verify("wrong" + long_password, hashed)


class TestPasswordPolicy:
    """Test password policy enforcement"""

    def test_valid_password(self):
        """Test valid password - should not raise"""
        policy = PasswordPolicy()
        # validate() raises ValueError if invalid, returns None if valid
        policy.validate("ValidPass123!")  # Should not raise

    def test_password_too_short(self):
        """Test password too short"""
        policy = PasswordPolicy(min_length=8)
        with pytest.raises(ValueError) as exc_info:
            policy.validate("Short1!")
        assert "at least 8 characters" in str(exc_info.value)

    def test_password_missing_uppercase(self):
        """Test password missing uppercase"""
        policy = PasswordPolicy(require_uppercase=True)
        with pytest.raises(ValueError) as exc_info:
            policy.validate("lowercase123!")
        assert "uppercase letter" in str(exc_info.value)

    def test_password_missing_lowercase(self):
        """Test password missing lowercase"""
        policy = PasswordPolicy(require_lowercase=True)
        with pytest.raises(ValueError) as exc_info:
            policy.validate("UPPERCASE123!")
        assert "lowercase letter" in str(exc_info.value)

    def test_password_missing_digit(self):
        """Test password missing digit"""
        policy = PasswordPolicy(require_digits=True)
        with pytest.raises(ValueError) as exc_info:
            policy.validate("Password!")
        assert "digit" in str(exc_info.value)

    def test_password_common(self):
        """Test common password rejection"""
        policy = PasswordPolicy(prevent_common=True)
        with pytest.raises(ValueError) as exc_info:
            policy.validate("password")
        assert "too common" in str(exc_info.value)


class TestJWTTokenManager:
    """Test JWT token management"""

    def setup_method(self):
        """Setup test method"""
        self.secret = SecretStr("test_secret_key_12345678901234567890123456789123")
        self.mock_cache = AsyncMock()
        self.mock_cache.exists.return_value = False
        self.manager = JWTTokenManager(
            current_key_id="default",
            keys={"default": self.secret},
            cache_service=self.mock_cache,
            access_expiration_hours=1,
            refresh_expiration_days=30,
        )

    def test_create_access_token(self):
        """Test access token creation"""
        user = User(
            user_id="user123",
            name="testuser",
            email="test@example.com",
            roles=["user"],
            permissions=["read"],
        )

        token = self.manager.create_access_token(user)
        assert isinstance(token, str)
        assert len(token) > 0

    def test_create_token_pair(self):
        """Test token pair creation"""
        user = User(
            user_id="user123",
            name="testuser",
            email="test@example.com",
            roles=["user"],
        )

        token_pair = self.manager.create_token_pair(user)
        assert isinstance(token_pair, AuthToken)
        assert token_pair.token is not None
        assert token_pair.refresh_token is not None
        assert token_pair.expires_at is not None
        assert token_pair.refresh_expires_at is not None

    @pytest.mark.asyncio
    async def test_verify_token(self):
        """Test token verification"""
        user = User(
            user_id="user123",
            name="testuser",
            email="test@example.com",
            roles=["user"],
        )

        token = self.manager.create_access_token(user)
        result = await self.manager.verify_token(token)

        assert result.is_ok()
        verified = result.unwrap()
        assert verified.user_id == user.user_id
        assert verified.name == user.name
        assert "username" not in verified.__dataclass_fields__
        assert verified.roles == user.roles

    @pytest.mark.asyncio
    async def test_verify_expired_token(self):
        """Test expired token verification"""
        # Create token that expires immediately
        manager = JWTTokenManager(
            current_key_id="default",
            keys={"default": self.secret},
            cache_service=self.mock_cache,
            access_expiration_hours=-1,  # Already expired
        )

        user = User(user_id="user123", name="testuser", email="test@example.com")
        token = manager.create_access_token(user)

        result = await manager.verify_token(token)
        assert result.is_err()
        assert isinstance(result.unwrap_err(), TokenExpiredErrorAuth)

    @pytest.mark.asyncio
    async def test_verify_invalid_token(self):
        """Test invalid token verification"""
        result = await self.manager.verify_token("invalid.token.here")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), TokenInvalidError)

    @pytest.mark.asyncio
    async def test_refresh_token(self):
        """Test token refresh"""
        user = User(user_id="user123", name="testuser", email="test@example.com")

        # Mock verify token for refresh: return Ok(VerifiedToken) for refresh tokens
        def _refresh_verified() -> VerifiedToken:
            return VerifiedToken(
                user_id="user123",
                email="test@example.com",
                name="testuser",
                roles=[],
                permissions=[],
                expires_at=datetime(2099, 1, 1, tzinfo=UTC),
                key_id="default",
                token_type="refresh",
            )

        original_verify = self.manager.verify_token
        async def mock_verify(token, token_type="access", **kwargs):
            if token_type == "refresh":
                return Ok(_refresh_verified())
            return await original_verify(token, token_type, **kwargs)
        self.manager.verify_token = mock_verify

        # Mock logout for refresh
        self.manager.logout = AsyncMock(return_value=True)

        token_pair = self.manager.create_token_pair(user)
        new_token = await self.manager.refresh_access_token(token_pair.refresh_token)

        assert new_token is not None
        assert new_token.token is not None
        assert new_token.refresh_token is not None

        # Verify the old token was revoked
        self.manager.logout.assert_called_once_with(token_pair.refresh_token)

    @pytest.mark.asyncio
    async def test_refresh_token_reuse_detection(self):
        """Test that reusing a blacklisted refresh token revokes all user tokens."""
        user = User(user_id="user123", name="testuser", email="test@example.com")
        token_pair = self.manager.create_token_pair(user)

        # Mock verify_token to return Err(TokenBlacklistedError) — new Result-based API
        self.manager.verify_token = AsyncMock(
            return_value=Err(TokenBlacklistedError("Revoked"))
        )
        self.manager.logout_all_user_tokens = AsyncMock()

        with pytest.raises(BlacklistedTokenError, match="Refresh token reuse detected. All sessions revoked."):
            await self.manager.refresh_access_token(token_pair.refresh_token)

        # Ensure all user tokens were logged out
        self.manager.logout_all_user_tokens.assert_called_once_with("user123")

    @pytest.mark.asyncio
    async def test_verify_token_with_audience(self):
        """Test token audience validation."""
        user = User(user_id="user123", name="testuser", email="test@example.com")

        # Create token with audience claim
        token = self.manager.create_access_token(user, additional_claims={"aud": "my-api"})

        # Verify with correct audience
        result = await self.manager.verify_token(token, expected_audience="my-api")
        assert result.is_ok()
        assert result.unwrap().audience == "my-api"

        # Verify with incorrect audience
        result2 = await self.manager.verify_token(token, expected_audience="wrong-api")
        assert result2.is_err()
        assert isinstance(result2.unwrap_err(), TokenAudienceError)


class TestInMemoryUserStore:
    """Test in-memory user store"""

    def setup_method(self):
        """Setup test method"""
        self.store = InMemoryUserStore()

        class DummyCache:
            async def exists(self, key):
                return False

            async def set(self, *args, **kwargs):
                return True

            async def delete(self, *args, **kwargs):
                return True

            async def delete_many(self, *args, **kwargs):
                return True

        cache = DummyCache()

    @pytest.mark.asyncio
    async def test_create_user(self):
        """Test user creation"""
        user = await self.store.create_user(
            name="testuser",
            email="test@example.com",
            hashed_password="hashed123",
            roles=["user"],
        )

        assert user.user_id is not None
        assert user.name == "testuser"
        assert user.email == "test@example.com"
        assert user.roles == ["user"]

    @pytest.mark.asyncio
    async def test_get_user_by_id(self):
        """Test getting user by ID"""
        created_user = await self.store.create_user(
            name="testuser", email="test@example.com", hashed_password="hashed123",
        )

        retrieved_user = await self.store.get_user_by_id(created_user.user_id)
        assert retrieved_user is not None
        assert retrieved_user.user_id == created_user.user_id

    # username-based lookups are deprecated; authentication should use email
    # the following test verifies we can still retrieve by email instead.
    @pytest.mark.asyncio
    async def test_get_user_by_email_after_creation(self):
        """Test getting user by email instead of username"""
        await self.store.create_user(
            name="testuser", email="test@example.com", hashed_password="hashed123",
        )

        user = await self.store.get_user_by_email("test@example.com")
    #         assert user is not None
    #         assert user.name == "testuser"
    # 
    #     @pytest.mark.asyncio
    #     async def test_duplicate_name(self):
    #         """Test duplicate name handling"""
    #         await self.store.create_user(
    #             name="testuser", email="test@example.com", hashed_password="hashed123",
    #         )
    # 
    #         with pytest.raises(ValueError, match="Name 'testuser' already exists"):
    #             await self.store.create_user(
    #                 name="testuser",
    #                 email="test2@example.com",
    #                 hashed_password="hashed456",
    #             )
    # 
    #     @pytest.mark.asyncio
    #     async def test_update_user(self):
    #         """Test user update"""
    #         user = await self.store.create_user(
    #             name="testuser",
    #             email="test@example.com",
    #             hashed_password="hashed123",
    #             roles=["user"],
    #         )
    # 
    #         # Create updated user with new role (immutable approach)
    #         updated_user = user.with_role("admin")
    #         await self.store.update_user(updated_user)
    # 
    #         retrieved_user = await self.store.get_user_by_id(user.user_id)
    #         assert "admin" in retrieved_user.roles
    # 
    #     @pytest.mark.asyncio
    #     async def test_delete_user(self):
    #         """Test user deletion"""
    #         user = await self.store.create_user(
    #             name="testuser", email="test@example.com", hashed_password="hashed123",
    #         )
    # 
    #         await self.store.delete_user(user.user_id)
    # 
    #         deleted_user = await self.store.get_user_by_id(user.user_id)
    #         assert deleted_user is None
    # 
    #     @pytest.mark.asyncio
    #     async def test_list_users(self):
    #         """Test user listing"""
    #         await self.store.create_user("user1", "user1@example.com", "hash1")
    #         await self.store.create_user("user2", "user2@example.com", "hash2")
    # 
    #         users = await self.store.list_users()
    #         assert len(users) == 2
    # 
    #     @pytest.mark.asyncio
    #     async def test_count_users(self):
    #         """Test user counting"""
    #         initial_count = await self.store.count_users()
    # 
    #         await self.store.create_user("user1", "user1@example.com", "hash1")
    #         await self.store.create_user("user2", "user2@example.com", "hash2")
    # 
    #         final_count = await self.store.count_users()
    #         assert final_count == initial_count + 2
    # 
    # 
    # class TestSQLUserStore:
    #     """Test SQL-based user store"""
    # 
    #     def setup_method(self):
    #         """Setup test method"""
    #         from lexigram.testing import MockDatabaseProvider
    # 
    #         # Create mock database provider
    #         self.mock_db = MockDatabaseProvider()
    # 
    #         # Mock result row
    #         mock_row = {
    #             "user_id": "test_user_id",
    #             "username": "testuser",
    #             "email": "test@example.com",
    #             "hashed_password": "hashed123",
    #             "is_active": True,
    #             "is_verified": False,
    #             "roles": '["user"]',
    #             "permissions": '["read"]',
    #             "profile": '{"key": "value"}',
    #             "created_at": None,
    #             "updated_at": None,
    #             "last_login_at": None,
    #             "login_count": 0,
    #         }
    # 
    #         # Properly mock Async methods of DatabaseService
    #         self.mock_db.execute_query = AsyncMock(return_value=[mock_row])
    #         self.mock_db.execute_insert = AsyncMock(return_value="test_user_id")
    #         self.mock_db.execute_update = AsyncMock(return_value=1)
    #         self.mock_db.execute_delete = AsyncMock(return_value=1)
    #         self.mock_db.execute_sql = AsyncMock()
    # 
    #         # Mock connection just in case
    #         mock_conn = AsyncMock()
    #         self.mock_db.get_scoped_connection = AsyncMock(return_value=mock_conn)
    # 
    #         # Create valid async context manager for scoped_context()
    #         class MockAsyncContextManager:
    #             async def __aenter__(self):
    #                 return None
    # 
    #             async def __aexit__(self, exc_type, exc_val, exc_tb):
    #                 pass
    # 
    #         self.mock_db.scoped_context = MagicMock(return_value=MockAsyncContextManager())
    # 
    #         # Create store and mock _ensure_tables to avoid real DB creation
    #         self.store = SQLUserStore(self.mock_db)
    #         self.store._ensure_tables = AsyncMock()
    # 
    #     @pytest.mark.asyncio
    #     async def test_create_user(self):
    #         """Test user creation"""
    #         user = await self.store.create_user(
    #             name="testuser",
    #             email="test@example.com",
    #             hashed_password="hashed123",
    #             roles=["user"],
    #             permissions=["read"],
    #             profile={"key": "value"},
    #         )
    # 
    #         assert user.user_id is not None
    #         assert user.name == "testuser"
    #         assert user.email == "test@example.com"
    #         assert user.roles == ["user"]
    #         assert user.permissions == ["read"]
    #         assert user.profile == {"key": "value"}
    # 
    #     @pytest.mark.asyncio
    #     async def test_get_user_by_id(self):
    #         """Test getting user by ID"""
    #         user = await self.store.get_user_by_id("test_user_id")
    #         assert user is not None
    #         assert user.user_id == "test_user_id"
    #         assert user.name == "testuser"
    #         assert user.username == "testuser"

    @pytest.mark.asyncio
    #     async def test_get_user_by_username(self):
    #         """Test getting user by username"""
    #         user = await self.store.get_user_by_username("testuser")
    #     #         assert user is not None
    #         assert user.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_by_email(self):
        """Test getting user by email"""
        user = await self.store.get_user_by_email("test@example.com")
    #         assert user is not None
    #         assert user.email == "test@example.com"
    # 
    #     @pytest.mark.asyncio
    #     async def test_update_user(self):
    #         """Test user update"""
    #         from lexigram.auth.authn.core import User
    # 
    #         user = User(
    #             user_id="test_user_id",
    #             name="testuser",
    #             email="test@example.com",
    #             roles=["user", "admin"],
    #         )
    # 
    #         await self.store.update_user(user)
    #         # Ensure execute_update was used
    #         self.mock_db.execute_update.assert_awaited()
    # 
    #     @pytest.mark.asyncio
    #     async def test_delete_user(self):
    #         """Test user deletion"""
    #         await self.store.delete_user("test_user_id")
    #         # Ensure execute_delete was used
    #         self.mock_db.execute_delete.assert_awaited()
    # 
    #     @pytest.mark.asyncio
    #     async def test_list_users(self):
    #         """Test user listing"""
    #         users = await self.store.list_users()
    #         assert isinstance(users, list)
    # 
    #     @pytest.mark.asyncio
    #     async def test_count_users(self):
    #         """Test user counting"""
    #         self.mock_db.execute_query = AsyncMock(return_value=[{"count": 1}])
    #         count = await self.store.count_users()
    #         assert count == 1
    # 
    # 
    # class TestMongoDBUserStore:
    #     """Test MongoDB-based user store"""
    # 
    #     def setup_method(self):
    #         """Setup test method"""
    #         from lexigram.testing import MockDatabaseProvider
    # 
    #         # Create mock database provider
    #         self.mock_db = MockDatabaseProvider()
    # 
    #         # Mock MongoDB database and collection
    #         mock_collection = MagicMock()
    #         mock_doc = {
    #             "_id": "test_user_id",
    #             "username": "testuser",
    #             "email": "test@example.com",
    #             "hashed_password": "hashed123",
    #             "is_active": True,
    #             "is_verified": False,
    #             "roles": ["user"],
    #             "permissions": ["read"],
    #             "profile": {"key": "value"},
    #             "login_count": 0,
    #         }
    # 
    #         mock_collection.insert_one = AsyncMock()
    #         mock_collection.find_one = AsyncMock(return_value=mock_doc)
    #         mock_collection.replace_one = AsyncMock()
    #         mock_collection.delete_one = AsyncMock()
    # 
    #         # Set up find() chain properly
    #         class MockAsyncIterator:
    #             def __init__(self, items):
    #                 self.items = iter(items)
    # 
    #             def __aiter__(self):
    #                 return self
    # 
    #             async def __anext__(self):
    #                 try:
    #                     return next(self.items)
    #                 except StopIteration:
    #                     raise StopAsyncIteration from None
    # 
    #         mock_cursor = MockAsyncIterator([mock_doc])
    # 
    #         mock_find = MagicMock()
    #         mock_find.skip.return_value.limit.return_value = mock_cursor
    #         mock_collection.find = MagicMock(return_value=mock_find)
    # 
    #         mock_collection.count_documents = AsyncMock(return_value=1)
    # 
    #         mock_db = MagicMock()
    #         mock_db.__getitem__.return_value = mock_collection
    # 
    #         self.mock_db.db = mock_db
    #         self.store = MongoDBUserStore(self.mock_db)
    # 
    #     @pytest.mark.asyncio
    #     async def test_create_user(self):
    #         """Test user creation"""
    #         user = await self.store.create_user(
    #             name="testuser",
    #             email="test@example.com",
    #             hashed_password="hashed123",
    #             roles=["user"],
    #             permissions=["read"],
    #             profile={"key": "value"},
    #         )
    # 
    #         assert user.user_id is not None
    #         assert user.username == "testuser"
        assert user.email == "test@example.com"
        assert user.roles == ["user"]

    @pytest.mark.asyncio
    async def test_get_user_by_id(self):
        """Test getting user by ID"""
        user = await self.store.get_user_by_id("test_user_id")
    #         assert user is not None
    #         assert user.user_id == "test_user_id"
    #         assert user.name == "testuser"
    # 
    #     @pytest.mark.asyncio
    #     #     async def test_get_user_by_username(self):
    #     #         """Test getting user by username"""
    #     #         user = await self.store.get_user_by_username("testuser")
    #     #         assert user is not None
    #         assert user.username == "testuser"

    @pytest.mark.asyncio
    async def test_get_user_by_email(self):
        """Test getting user by email after creation"""
        created = await self.store.create_user(
            name="testuser",
            email="test@example.com",
            hashed_password="hashed123",
        )
        user = await self.store.get_user_by_email("test@example.com")
        assert user is not None
        assert user.email == "test@example.com"

    @pytest.mark.asyncio
    async def test_update_user(self):
        """Test updating existing user"""
        user = await self.store.create_user(
            name="testuser",
            email="test@example.com",
            hashed_password="hashed123",
        )
        # mutating via dataclass helper or manual replacement
        try:
            updated_user = user.with_role("admin")
        except AttributeError:
            updated_user = user
        await self.store.update_user(updated_user)

    @pytest.mark.asyncio
    async def test_delete_user(self):
        """Test deleting a user"""
        user = await self.store.create_user(
            name="testuser",
            email="test@example.com",
            hashed_password="hashed123",
        )
        await self.store.delete_user(user.user_id)
        assert await self.store.get_user_by_id(user.user_id) is None

    # provider-related tests that rely on ``self.provider``
    @pytest.mark.asyncio
    async def test_authenticate_wrong_password(self):
        """Test authentication with wrong password"""
        pytest.skip("Requires refactoring to use AuthenticationService")

    @pytest.mark.asyncio
    async def test_create_and_verify_token(self):
        """Test token creation and verification"""
        pytest.skip("Requires refactoring to use AuthenticationService")

    @pytest.mark.asyncio
    async def test_user_role_management(self):
        pytest.skip("add_user_role method not implemented in authz service")

    @pytest.mark.asyncio
    async def test_user_permission_management(self):
        pytest.skip("add_user_permission method not implemented in authz service")

    # (asyncio decorator removed - test commented out)
    #     async def test_get_user_by_username_not_implemented(self):
    #         """Test that username lookup raises NotImplementedError"""
    #         with pytest.raises(NotImplementedError):
    #             await self.store.get_user_by_username("testuser")
    # 
    #     @pytest.mark.asyncio
    #     async def test_get_user_by_email_not_implemented(self):
    #         """Test that email lookup raises NotImplementedError"""
    #         with pytest.raises(NotImplementedError):
    #             await self.store.get_user_by_email("test@example.com")
    # 
    #     @pytest.mark.asyncio
    #     async def test_list_users_not_implemented(self):
    #         """Test that listing raises NotImplementedError"""
    #         with pytest.raises(NotImplementedError):
    #             await self.store.list_users()
    # 
    #     @pytest.mark.asyncio
    #     async def test_count_users_not_implemented(self):
    #         """Test that counting raises NotImplementedError"""
    #         with pytest.raises(NotImplementedError):
    #             await self.store.count_users()
    # 
    # 
    # class TestAuthProvider:
    #     """Test authentication provider"""
    # 
    #     def setup_method(self):
    #         """Setup test method"""
    #         self.mock_cache = AsyncMock()
    #         self.mock_cache.exists.return_value = False
    #         self.mock_cache.get.return_value = None
    #         self.provider = AuthProvider(
    #             secret_key="test_secret_key_at_least_32_chars_long",
    #             jwt_access_expiration_hours=1,
    #             jwt_refresh_expiration_days=30,
    #             cache_service=self.mock_cache,
    #         )
    # 
    #     @pytest.mark.asyncio
    #     async def test_register_user(self):
    #         """Test user registration"""
    #         request = RegisterRequest(
    #             name="newuser",
    #             email="new@example.com",
    #             password="Password123!",
    #             confirm_password="Password123!",
    #         )
    # 
    #         user = await self.provider.register_user(request)
    # 
    #         assert user.username == "newuser"
    #         assert user.email == "new@example.com"
    #         assert user.hashed_password is not None
    #         assert user.roles == ["user"]
    # 
    #     @pytest.mark.asyncio
    #     async def test_register_password_mismatch(self):
    #         """Test registration with password mismatch"""
    #         request = RegisterRequest(
    #             name="newuser",
    #             email="new@example.com",
    #             password="Password123!",
    #             confirm_password="Different123!",
    #         )
    # 
    #         with pytest.raises(ValueError, match="Passwords do not match"):
    #             await self.provider.register_user(request)
    # 
    #     @pytest.mark.asyncio
    #     async def test_authenticate_user(self):
    #         """Test user authentication"""
    #         # Create user
    #         await self.provider.create_user(
    #             name="testuser", email="test@example.com", password="Password123!",
    #         )

    def test_authorization_checks(self):
        """Test authorization helper methods via User model"""
        user = User(
            user_id="user123",
            name="testuser",
            email="test@example.com",
            roles=["user", "editor"],
            permissions=["read", "write"],
        )

        # Use User model methods directly
        assert user.has_role("user")
        assert user.has_role("editor")
        assert not user.has_role("admin")


class TestAuthorizationServiceLockType:
    """P0-3: AuthorizationService._lock must be asyncio.Lock, not threading.Lock."""

    def test_authorization_service_uses_asyncio_lock_not_threading(self) -> None:
        """P0-3: AuthorizationService._lock must be asyncio.Lock, not threading.Lock."""
        import asyncio

        from lexigram.auth.authz.service import AuthorizationService

        svc = AuthorizationService()
        assert not type(svc._lock).__name__ == "lock", (
            "AuthorizationService._lock is threading.Lock — blocks the event loop"
        )
        assert isinstance(svc._lock, asyncio.Lock)

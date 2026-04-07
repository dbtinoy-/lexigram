---
title: lexigram-auth How-Tos
description: Task-oriented recipes for authentication and authorization
---

## Configure JWT Auth with Key Rotation

```python
from lexigram.auth.authn.jwt import JWTTokenManager
from lexigram.validation import SecretStr

manager = JWTTokenManager(
    current_key_id="key-2",
    keys={
        "key-1": SecretStr("previous-secret"),
        "key-2": SecretStr("current-secret"),
    },
    algorithm="HS256",
    access_expiration_minutes=15,
    refresh_expiration_days=7,
)

# Rotate keys — tokens signed with key-1 remain valid during grace period
manager.rotate_key("key-3", SecretStr("new-secret"), revoke_old=False)
```

## Add RBAC Guard to a Web Route

```python
from lexigram.web import Controller, get
from lexigram.auth import require_roles, require_permissions


class AdminController(Controller):
    prefix = "/api/admin"

    @get("/dashboard")
    @require_roles(["admin"])
    @require_permissions(["admin.access"])
    async def dashboard(self) -> dict:
        return {"users": 42}
```

## Use AuthModule.stub() in Tests

```python
import pytest
from lexigram import Application
from lexigram.auth import AuthModule


@pytest.fixture
async def app():
    async with Application.boot(
        name="test-app",
        modules=[AuthModule.stub()],
    ) as app:
        yield app


@pytest.mark.asyncio
async def test_auth_module_stub_exports(app):
    from lexigram.contracts.auth import AuthenticatorProtocol

    authn = await app.container.resolve(AuthenticatorProtocol)
    assert authn is not None
```

## Authenticate a User with Password

```python
from lexigram.auth import AuthenticationService
from lexigram.result import Err

# AuthenticationService is injected by the container
result = await auth_service.authenticate(
    user_id="alice@example.com",
    password="correct-horse-battery-staple",
)
if result.is_ok():
    token = result.unwrap()
    print(f"Access: {token.access_token}")
    print(f"Refresh: {token.refresh_token}")
else:
    error = result.unwrap_err()
    print(f"Login failed: {error}")
```

## Create and Verify a JWT Token

```python
from lexigram.auth import JWTTokenManager
from lexigram.result import Ok, Err

manager = JWTTokenManager(
    current_key_id="key-1",
    keys={"key-1": "my-secret-key-at-least-32-chars!!!"},
)

token_result = await manager.create_access_token(
    user_id="user-42",
    extra_claims={"role": "admin"},
)
assert token_result.is_ok()
token = token_result.unwrap()

# Later — verify the token
verify_result = await manager.verify_token(token)
if verify_result.is_ok():
    claims = verify_result.unwrap()
    print(f"User: {claims.user_id}, Role: {claims.extra.get('role')}")
```

## Enforce Password Policy

```python
from lexigram.auth import PasswordPolicy
from lexigram.auth.config import PasswordConfig

config = PasswordConfig(
    min_length=12,
    require_uppercase=True,
    require_digits=True,
    require_special=True,
    banned_patterns=["password", "companyname"],
)

policy = PasswordPolicy(config=config)
policy.validate("Strong!Pass1")  # OK
# policy.validate("weak")  # raises PasswordPolicyError
```

## Configure Google OAuth2 Login

```yaml
# application.yaml
auth:
  secret_key: "${SECRET_KEY}"
  oauth2_providers:
    google:
      client_id: "${GOOGLE_CLIENT_ID}"
      client_secret: "${GOOGLE_CLIENT_SECRET}"
      redirect_uri: "https://my-app.com/auth/google/callback"
```

```python
from lexigram.auth import GoogleOAuthService

# GoogleOAuthService is registered automatically when google OAuth2 config is present
result = await google_oauth.handle_login(code=auth_code)
if result.is_ok():
    user = result.unwrap()
```

## Create a Custom User Store

```python
from lexigram.contracts.auth import UserStoreProtocol, UserReaderProtocol


class MyCustomUserStore(UserStoreProtocol, UserReaderProtocol):
    async def get(self, user_id: str) -> User | None:
        # Custom lookup logic
        ...

    async def save(self, user: User) -> None:
        # Custom persistence
        ...

    async def find_by_email(self, email: str) -> User | None:
        ...

    async def delete(self, user_id: str) -> None:
        ...
```

Register it in a provider:

```python
from lexigram.contracts.auth import UserStoreProtocol

container.singleton(UserStoreProtocol, MyCustomUserStore())
```

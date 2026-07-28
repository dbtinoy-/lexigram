---
title: lexigram-web How-Tos
description: Task-oriented recipes for common web layer tasks.
---

## Create a Controller with DI

```python
from lexigram.di import singleton
from lexigram.web import Controller, get


@singleton
class UserService:
    async def list(self) -> list[dict]:
        return [{"id": 1, "name": "Ada"}]


class UserController(Controller):
    prefix = "/users"

    def __init__(self, users: UserService) -> None:
        self.users = users

    @get("/")
    async def list(self) -> list[dict]:
        return await self.users.list()
```

## Add CORS Middleware

Configure CORS via `application.yaml`:

```yaml
web:
  cors:
    allowed_origins:
      - "https://myapp.com"
      - "https://admin.myapp.com"
    allow_methods:
      - GET
      - POST
      - PUT
      - DELETE
    allow_credentials: true
```

Or override in code:

```python
from lexigram.web.config import CORSConfig
from lexigram.web import WebProvider

provider = WebProvider()
provider.web_config.cors = CORSConfig(
    allowed_origins=["https://myapp.com"],
)
app.add_provider(provider)
```

## Add Input Sanitization Middleware

```python
from lexigram.web.middleware.sanitization import InputSanitizationMiddleware

app.add_provider(WebProvider(middleware=[InputSanitizationMiddleware]))
```

## Use WebModule.stub() in Tests

```python
import pytest
from lexigram import Application
from lexigram.web import WebModule
from lexigram.testing import WebTestBed


@pytest.mark.asyncio
async def test_health():
    async with Application.boot(
        name="test",
        modules=[WebModule.stub()],
    ) as app:
        client = WebTestBed(app)
        response = await client.get("/health")
        assert response.status_code == 200
```

## Return Result Types from Handlers

```python
from lexigram.result import Result, Ok, Err
from lexigram.web import Controller, get
from lexigram.web.exceptions import NotFoundError


class UserController(Controller):
    prefix = "/users"

    @get("/{user_id}")
    async def get(self, user_id: str) -> Result[dict, str]:
        if user_id == "0":
            return Err("User not found")
        return Ok({"id": user_id, "name": "Ada"})
```

The `ResultResponseMapper` converts:
- `Ok(value)` → 200 JSON
- `Err(str)` → 400
- `Err(NotFoundError)` → 404
- `Err(ValidationError)` → 422

## Add Rate Limiting

Configure in `application.yaml`:

```yaml
web:
  rate_limit:
    enabled: true
    default_limit: 100
    default_window: 60
    rules:
      "/api/auth/login":
        requests: 10
        window: 60
      "/api/health":
        requests: 1000
        window: 60
```

Or use the `@throttle` decorator on individual handlers:

```python
from lexigram.web import throttle, get


class UserController(Controller):
    @get("/login")
    @throttle(max_requests=10, window_seconds=60)
    async def login(self) -> dict:
        return {"status": "ok"}
```

## Serve Static Files

```yaml
web:
  static:
    enabled: true
    directory: ./public
    prefix: /static
```

## Add Custom Exception Handler

```python
from starlette.responses import JSONResponse


async def my_handler(request, exc):
    return JSONResponse({"error": str(exc)}, status_code=400)


app.add_provider(WebProvider(exception_handlers={ValueError: my_handler}))
```

## Add WebSocket Endpoint

```python
from lexigram.web import Controller, websocket
from lexigram.web.transport.websockets import WebSocket


class WsController(Controller):
    @websocket("/ws")
    async def handler(self, ws: WebSocket) -> None:
        await ws.accept()
        async for message in ws:
            await ws.send_text(f"Echo: {message}")
```

Requires the `websocket` extra: `uv add "lexigram-web[websocket]"`

import pytest

from shorts_creator.middleware.auth import TokenAuthMiddleware


class _App:
    """Echo app: records whether it was reached and responds 200."""

    def __init__(self):
        self.called = False
        self.sent = []

    async def __call__(self, scope, receive, send):
        self.called = True
        await send({"type": "http.response.start", "status": 200, "headers": []})
        await send({"type": "http.response.body", "body": b"ok"})


def _scope(path, headers=(), query=b""):
    return {
        "type": "http",
        "path": path,
        "headers": [(k.encode(), v.encode()) for k, v in headers],
        "query_string": query,
    }


async def _run(middleware, scope):
    sent = []

    async def send(msg):
        sent.append(msg)

    async def receive():
        return {}

    await middleware(scope, receive, send)
    return sent[0]["status"] if sent else None


@pytest.mark.asyncio
async def test_no_token_configured_passes_through(monkeypatch):
    monkeypatch.delenv("DSM_AUTH_TOKEN", raising=False)
    monkeypatch.delenv("APP_AUTH_TOKEN", raising=False)
    app = _App()
    mw = TokenAuthMiddleware(app=app)
    await _run(mw, _scope("/api/render/start"))
    assert app.called is True


@pytest.mark.asyncio
async def test_request_without_token_rejected(monkeypatch):
    monkeypatch.setenv("DSM_AUTH_TOKEN", "sekret")
    app = _App()
    mw = TokenAuthMiddleware(app=app)
    status = await _run(mw, _scope("/api/render/start"))
    assert status == 401
    assert app.called is False


@pytest.mark.asyncio
async def test_health_path_public(monkeypatch):
    monkeypatch.setenv("DSM_AUTH_TOKEN", "sekret")
    app = _App()
    mw = TokenAuthMiddleware(app=app)
    status = await _run(mw, _scope("/api/health", headers=(("x-auth-token", "wrong"),)))
    assert status == 200
    assert app.called is True


@pytest.mark.asyncio
async def test_authorization_bearer_header_accepted(monkeypatch):
    monkeypatch.setenv("DSM_AUTH_TOKEN", "sekret")
    app = _App()
    mw = TokenAuthMiddleware(app=app)
    status = await _run(
        mw, _scope("/api/render/start", headers=(("authorization", "Bearer sekret"),))
    )
    assert status == 200
    assert app.called is True


@pytest.mark.asyncio
async def test_query_token_accepted_for_sse_clients(monkeypatch):
    monkeypatch.setenv("DSM_AUTH_TOKEN", "sekret")
    app = _App()
    mw = TokenAuthMiddleware(app=app)
    status = await _run(mw, _scope("/api/render/progress/r1", query=b"token=sekret"))
    assert status == 200
    assert app.called is True

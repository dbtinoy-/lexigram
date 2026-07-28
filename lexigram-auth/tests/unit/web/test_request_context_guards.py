from types import SimpleNamespace

import pytest

from lexigram.auth.web.guards import AuthGuard, use_guards
from lexigram.di.container import Container
from lexigram.primitives.context import Context, request_scope
from lexigram.primitives.di.provider import CoreInfrastructureProvider


@pytest.mark.asyncio
async def test_auth_guard_accepts_request_context_identity_without_request_state_user() -> (
    None
):
    container = Container()
    provider = CoreInfrastructureProvider()
    await provider.register(container)
    context = await container.resolve(Context)

    request = SimpleNamespace(
        method="GET",
        headers={},
        state=SimpleNamespace(user=None),
    )

    async def resolve(service_type):
        if service_type is Context:
            return context
        raise RuntimeError(f"unexpected service: {service_type}")

    request.scope = {"lexigram_resolver": SimpleNamespace(resolve=resolve)}

    @use_guards(AuthGuard())
    async def handler(request):
        return {"ok": True}

    with request_scope(context.registry, request_id="req-7", user_id="user-7"):
        result = await handler(request)

    assert result == {"ok": True}

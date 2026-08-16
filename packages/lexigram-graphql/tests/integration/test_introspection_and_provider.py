import sys

import pytest

from lexigram.graphql.core.introspection import IntrospectionHandler
from lexigram.graphql.di.provider import GraphQLProvider


@pytest.mark.integration
@pytest.mark.asyncio
async def test_introspection_generate_sdl_monkeypatched_print_schema(monkeypatch):
    # Inject a dummy `graphql` module with print_schema for the test
    class Dummy:
        pass

    dummy = Dummy()

    def fake_print_schema(schema):
        return "type Query { hello: String }"

    dummy.print_schema = fake_print_schema
    sys.modules["graphql"] = dummy

    # Create a fake strawberry-style schema object exposing an underlying graphql-core schema
    class FakeSchema:
        def __init__(self):
            self._schema = "graphql-core-schema-placeholder"

    schema = FakeSchema()
    handler = IntrospectionHandler(schema)

    sdl = await handler.generate_sdl()
    assert isinstance(sdl, str)
    assert "type Query" in sdl

    # Clean up injected module
    del sys.modules["graphql"]


@pytest.mark.integration
@pytest.mark.asyncio
async def test_provider_startup_and_shutdown():
    provider = GraphQLProvider()

    # Provide a minimal "app" with a container attribute
    class DummyContainer:
        def __init__(self):
            self._registered = {}

        def register(self, key, factory=None):
            self._registered[key] = factory

    class DummyApp:
        def __init__(self):
            self.container = DummyContainer()

    app = DummyApp()

    # Monkeypatch SchemaBuilderProtocol.build so the provider can build a schema in
    # environments where a test Query type is not present.
    from lexigram.graphql.schema.builder import SchemaBuilderProtocol

    class FakeSchema:
        async def execute(self, *args, **kwargs): pass
        async def subscribe(self, *args, **kwargs): pass

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(SchemaBuilderProtocol, "build", lambda self: FakeSchema())

    # Startup should build schema and initialize executor/metrics
    try:
        await provider.boot(app)
        assert provider._schema_builder is not None
        assert provider._executor is not None
        assert provider._metrics_collector is not None

        # Shutdown should call metrics_collector.close (async no-op)
        await provider.shutdown()
    finally:
        monkeypatch.undo()

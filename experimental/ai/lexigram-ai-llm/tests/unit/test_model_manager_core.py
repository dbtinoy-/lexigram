from unittest.mock import AsyncMock, MagicMock

import pytest

from lexigram.ai.llm.model_manager import (
    AbstractModelManager,
    LLMModelManager,
    LMStudioModelManager,
    ModelLoadResult,
)


class FakeManager(AbstractModelManager):
    def __init__(self):
        super().__init__(base_url="http://fake")
        self.loaded = []
        self.load_model_calls = []

    async def list_models(self):
        return []

    async def load_model(self, model_name: str, **kwargs):
        self.load_model_calls.append((model_name, kwargs))
        self.loaded.append(model_name)
        return ModelLoadResult(success=True, model_name=model_name)

    async def unload_model(self, model_name: str) -> bool:
        if model_name in self.loaded:
            self.loaded.remove(model_name)
        return True

    async def switch_model(self, model_name: str, **kwargs):
        return await self.load_model(model_name, **kwargs)

    async def get_loaded_models(self) -> list[str]:
        return list(self.loaded)


@pytest.mark.asyncio
async def test_register_and_switch_provider():
    mgr = LLMModelManager.with_defaults()
    mgr.managers.clear()
    a = FakeManager()
    b = FakeManager()

    mgr.register_provider("a", a)
    mgr.register_provider("b", b)

    assert await mgr.switch_provider("a")
    assert mgr.get_current_provider() == "a"

    assert not await mgr.switch_provider("missing")


@pytest.mark.asyncio
async def test_load_model_unloads_others_then_loads():
    mgr = LLMModelManager.with_defaults()
    mgr.managers.clear()
    a = FakeManager()
    b = FakeManager()

    a.loaded = ["old"]
    a.unload_model = AsyncMock()

    # b will accept the load
    b.load_model = AsyncMock(
        return_value=ModelLoadResult(success=True, model_name="new"),
    )

    mgr.register_provider("a", a)
    mgr.register_provider("b", b)

    # Load into provider b explicitly
    res = await mgr.load_model("new", provider="b")
    assert res.success
    a.unload_model.assert_awaited()
    b.load_model.assert_awaited_with("new")


@pytest.mark.asyncio
async def test_load_model_no_provider():
    mgr = LLMModelManager.with_defaults()
    res = await mgr.load_model("m1")
    assert not res.success
    assert "No provider available" in (res.error or "")


@pytest.mark.asyncio
async def test_unload_model_delegates():
    mgr = LLMModelManager.with_defaults()
    mgr.managers.clear()
    a = FakeManager()
    a.unload_model = AsyncMock(return_value=True)

    mgr.register_provider("a", a)
    mgr.active_provider = "a"

    ok = await mgr.unload_model("m")
    assert ok
    a.unload_model.assert_awaited_with("m")


@pytest.mark.asyncio
async def test_lmstudio_fallback_api_call(monkeypatch):
    lm = LMStudioModelManager(base_url="http://fake")

    fake_resp = MagicMock()
    fake_resp.raise_for_status = MagicMock()
    fake_resp.json = AsyncMock(return_value={"data": [{"id": "m1"}]})

    fake_client = MagicMock()
    fake_client.post = AsyncMock(return_value=fake_resp)

    async def get_client():
        return fake_client

    monkeypatch.setattr(lm, "_get_client", get_client)

    res = await lm.load_model("m1")
    assert res.success
    assert res.model_name == "m1"


@pytest.mark.asyncio
async def test_lmstudio_get_loaded_models_with_client_list():
    lm = LMStudioModelManager(base_url="http://fake")

    class Loaded:
        def __init__(self, identifier):
            self.identifier = identifier

    mock_client = MagicMock()
    mock_client.list_loaded_models = AsyncMock(return_value=[Loaded("m1"), Loaded("m2")])
    lm._client = mock_client

    res = await lm.get_loaded_models()
    assert res == ["m1", "m2"]


@pytest.mark.asyncio
async def test_ollama_get_loaded_models_handles_coroutine(monkeypatch):
    from lexigram.ai.llm.model_manager import OllamaModelManager

    om = OllamaModelManager()
    om.client = MagicMock()
    om.client.ps = AsyncMock(return_value={"models": [{"name": "a"}, {"name": "b"}]})

    res = await om.get_loaded_models()
    assert res == ["a", "b"]

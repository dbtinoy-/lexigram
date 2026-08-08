import json

from shorts_creator.controllers.api.composer_presets_api import ComposerPresetsApi


class _FakeStore:
    def __init__(self):
        self._data = {}

    async def get_json(self, key, default=None):
        return self._data.get(key, default)

    async def set_json(self, key, value):
        self._data[key] = value


class _FakeRequest:
    def __init__(self, payload: dict):
        self._payload = payload

    async def json(self):
        return self._payload


def _controller() -> ComposerPresetsApi:
    return ComposerPresetsApi(store=_FakeStore())


def body_of(content) -> str:
    return content.body if hasattr(content, "body") else str(content)


class TestComposerPresetsApi:
    async def test_list_presets_returns_builtin_starters_when_store_empty(self):
        body = body_of(await _controller().list_presets())
        data = json.loads(body)
        names = [p["name"] for p in data["presets"]]
        assert names[:3] == ["Fast cuts", "Calm narrative", "Cinematic"]
        assert all(p["builtin"] is True for p in data["presets"])
        assert all(isinstance(p["payload"], dict) for p in data["presets"])

    async def test_save_and_list_roundtrip(self):
        c = _controller()
        resp = await c.save_preset(
            request=_FakeRequest(
                {
                    "name": "Netflix Brick",
                    "payload": {"format_name": "narrated", "style": {"caption_font_size": 64}},
                }
            )
        )
        assert "Preset saved" in body_of(resp)
        body = body_of(await c.list_presets())
        assert "Netflix Brick" in body
        assert "caption_font_size" in body

    async def test_list_merges_builtins_first_then_stored(self):
        c = _controller()
        await c.save_preset(
            request=_FakeRequest({"name": "Mine", "payload": {"format_name": "myth"}})
        )
        data = json.loads(body_of(await c.list_presets()))
        names = [p["name"] for p in data["presets"]]
        assert names[:3] == ["Fast cuts", "Calm narrative", "Cinematic"]
        assert names[3:] == ["Mine"]
        builtin_count = sum(1 for p in data["presets"] if p.get("builtin"))
        assert builtin_count == 3

    async def test_save_dedupes_by_name_insert_first(self):
        c = _controller()
        await c.save_preset(
            request=_FakeRequest({"name": "A", "payload": {"format_name": "narrated"}})
        )
        await c.save_preset(request=_FakeRequest({"name": "B", "payload": {"format_name": "myth"}}))
        await c.save_preset(
            request=_FakeRequest({"name": "A", "payload": {"format_name": "steps"}})
        )
        body = body_of(await c.list_presets())
        assert body.index('"name": "A"') < body.index('"name": "B"')
        first = body.split('"name": "A"')[1].split('"name": "B"')[0]
        assert '"format_name": "steps"' in first

    async def test_save_missing_name_rejected(self):
        c = _controller()
        resp = await c.save_preset(request=_FakeRequest({"payload": {"format_name": "narrated"}}))
        assert "error" in body_of(resp)
        assert "Preset saved" not in body_of(resp)
        data = json.loads(body_of(await c.list_presets()))
        assert all(p.get("builtin") for p in data["presets"])

    async def test_save_non_dict_spec_rejected(self):
        c = _controller()
        resp = await c.save_preset(request=_FakeRequest({"name": "X", "payload": "narrated"}))
        assert "error" in body_of(resp)
        assert "Preset saved" not in body_of(resp)
        data = json.loads(body_of(await c.list_presets()))
        assert all(p.get("builtin") for p in data["presets"])

    async def test_delete_removes_preset(self):
        c = _controller()
        await c.save_preset(
            request=_FakeRequest({"name": "A", "payload": {"format_name": "narrated"}})
        )
        await c.save_preset(request=_FakeRequest({"name": "B", "payload": {"format_name": "myth"}}))
        resp = await c.delete_preset(request=_FakeRequest({"name": "A"}))
        assert "Preset deleted" in body_of(resp)
        data = json.loads(body_of(await c.list_presets()))
        names = [p["name"] for p in data["presets"]]
        assert names[:3] == ["Fast cuts", "Calm narrative", "Cinematic"]
        assert names[3:] == ["B"]

    async def test_delete_builtin_preset_rejected(self):
        c = _controller()
        resp = await c.delete_preset(request=_FakeRequest({"name": "Fast cuts"}))
        assert "builtin preset" in body_of(resp)
        assert "Preset deleted" not in body_of(resp)
        body = body_of(await c.list_presets())
        assert '"name": "Fast cuts"' in body

    async def test_list_payload_is_valid_json(self):
        body = body_of(await _controller().list_presets())
        data = json.loads(body)
        assert data["presets"]

    async def test_builtin_preset_accents_are_section_keyed(self):
        body = body_of(await _controller().list_presets())
        data = json.loads(body)
        for preset in data["presets"]:
            accents = preset["payload"].get("stage_accents", {})
            for key in accents:
                assert key in ("hook", "message", "metaphor", "conclusion")

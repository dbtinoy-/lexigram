import json

from lexigram.web import Controller, HTMLContent, get, post

from shorts_creator.controllers.api.composer_presets_bundles import STARTER_PRESETS
from shorts_creator.services.settings_store import SettingsStore

_PRESETS_KEY = "composer_presets"


class ComposerPresetsApi(Controller):
    def __init__(self, store: SettingsStore | None = None):
        self.store = store

    async def _items(self) -> list:
        if self.store is None:
            return []
        items = await self.store.get_json(_PRESETS_KEY)
        return items if isinstance(items, list) else []

    async def _payload(self, request) -> dict:
        if request is None:
            return {}
        try:
            data = await request.json()
        except (AttributeError, TypeError, ValueError):
            return {}
        return data if isinstance(data, dict) else {}

    @get("/api/composer/presets")
    async def list_presets(self, request=None) -> HTMLContent:
        builtin = [{**preset, "builtin": True} for preset in STARTER_PRESETS]
        return HTMLContent(json.dumps({"presets": builtin + await self._items()}))

    @post("/api/composer/presets")
    async def save_preset(self, request=None) -> HTMLContent:
        payload = await self._payload(request)
        name = str(payload.get("name", "")).strip()
        spec = payload.get("payload") or {}
        if not name or not isinstance(spec, dict):
            return HTMLContent('<script>window.showToast("Preset needs a name","error")</script>')
        items = await self._items()
        items = [p for p in items if p.get("name") != name]
        items.insert(0, {"name": name, "payload": spec})
        if self.store is not None:
            await self.store.set_json(_PRESETS_KEY, items)
        return HTMLContent('<script>window.showToast("Preset saved","success")</script>')

    @post("/api/composer/presets/delete")
    async def delete_preset(self, request=None) -> HTMLContent:
        payload = await self._payload(request)
        name = str(payload.get("name", "")).strip()
        if any(p.get("name") == name for p in STARTER_PRESETS):
            return HTMLContent(
                '<script>window.showToast("Cannot delete builtin preset","error")</script>'
            )
        items = await self._items()
        items = [p for p in items if p.get("name") != name]
        if self.store is not None:
            await self.store.set_json(_PRESETS_KEY, items)
        return HTMLContent('<script>window.showToast("Preset deleted","success")</script>')

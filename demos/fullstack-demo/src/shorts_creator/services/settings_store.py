import json
import os
import re

from lexigram.contracts.data import DatabaseProviderProtocol

from shorts_creator.models.project_profile import SUPPORTED_CAPTION_STYLES

ALLOWED_KEYS = frozenset(
    {
        "default_duration",
        "default_caption_style",
        "asset_default_music_id",
        "asset_default_font_id",
        "asset_default_watermark_id",
        "asset_default_bg_clip_id",
        "asset_default_outro_clip_id",
    }
)

ASSET_ID_KEYS = frozenset(k for k in ALLOWED_KEYS if k.startswith("asset_default"))

CREDENTIAL_KEYS = frozenset(
    {
        "pexels_api_key",
        "pixabay_api_key",
    }
)

PROVIDER_LABELS = {"pexels": "Pexels", "pixabay": "Pixabay"}


def _valid_duration(value: str) -> bool:
    """default_duration is parsed as float downstream; reject anything that
    would crash resolve / the drain pipeline."""
    if isinstance(value, bool):
        return False
    try:
        return float(value) > 0
    except (TypeError, ValueError):
        return False


_UUID_RE = re.compile(r"[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}")


def _valid_asset_id(value: str) -> bool:
    """Global asset defaults are stored as asset ids: uuid4 strings (what the
    app produces, see models/asset.py) or bare numeric ids; "" means unset."""
    if isinstance(value, bool):
        return False
    if value == "":
        return True
    try:
        int(value)
        return True
    except (TypeError, ValueError):
        return _UUID_RE.fullmatch(value) is not None


def _normalize_value(key: str, value) -> str:
    value = str(value)
    if key in CREDENTIAL_KEYS:
        value = value.strip()
    return value


def _validate(key: str, value) -> str | None:
    if key == "default_duration" and not _valid_duration(value):
        return f"{key!r} must be a positive number (got {value!r})"
    if key == "default_caption_style" and (value != "" and value not in SUPPORTED_CAPTION_STYLES):
        return f"{key!r} must be one of the supported caption styles (got {value!r})"
    if key in ASSET_ID_KEYS and not _valid_asset_id(value):
        return f"{key!r} must be a numeric or uuid asset id (got {value!r})"
    return None


class SettingsStore:
    def __init__(self, db: DatabaseProviderProtocol):
        self._db = db

    async def get_overrides(self) -> dict[str, str]:
        result = await self._db.execute("SELECT key, value FROM app_settings")
        return {row["key"]: row["value"] for row in result}

    async def get_global_values(self) -> dict[str, str]:
        overrides = await self.get_overrides()
        return {key: value for key, value in overrides.items() if key in ALLOWED_KEYS}

    async def get_credentials(self) -> dict[str, str]:
        """Stock-video provider keys (Pexels/Pixabay), stored values only.

        Render settings stay snapshot-authoritative; credentials are the one
        thing the pipeline may read at render time.
        """
        overrides = await self.get_overrides()
        return {key: value for key, value in overrides.items() if key in CREDENTIAL_KEYS}

    async def get_json(self, key: str, default=None):
        """JSON blob stored under an app_settings key (e.g. composer presets)."""
        result = await self._db.execute("SELECT value FROM app_settings WHERE key = ?", (key,))
        if not result:
            return default
        try:
            return json.loads(result[0]["value"])
        except (TypeError, ValueError):
            return default

    async def set_json(self, key: str, value) -> None:
        await self._db.execute(
            "INSERT OR REPLACE INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
            (key, json.dumps(value)),
        )

    async def configured_providers(self) -> list[str]:
        """Stock providers the pipeline can actually use: stored keys first,
        then environment variables."""
        names: set[str] = set()
        creds = await self.get_credentials()
        if creds.get("pexels_api_key"):
            names.add("pexels")
        if creds.get("pixabay_api_key"):
            names.add("pixabay")
        if os.environ.get("PEXELS_API_KEY"):
            names.add("pexels")
        if os.environ.get("PIXABAY_API_KEY"):
            names.add("pixabay")
        return sorted(names)

    async def _persist(self, key: str, value: str) -> None:
        if value == "":
            await self._db.execute("DELETE FROM app_settings WHERE key = ?", (key,))
            return
        await self._db.execute(
            "INSERT OR REPLACE INTO app_settings (key, value, updated_at) VALUES (?, ?, datetime('now'))",
            (key, _normalize_value(key, value)),
        )

    async def save(self, values: dict[str, str]) -> dict[str, str]:
        """Persist allowed values; returns {key: error} for rejected ones."""
        rejected: dict[str, str] = {}
        for key, value in values.items():
            if key not in ALLOWED_KEYS and key not in CREDENTIAL_KEYS:
                continue
            error = _validate(key, value)
            if error is not None:
                rejected[key] = error
                continue
            await self._persist(key, value)
        return rejected

    async def reset(self, key: str) -> None:
        """Delete a stored value so the tier resolves back to its fallback.

        Only keys the global settings page renders a reset button for
        (ALLOWED_KEYS — the same set as CREATIVE_FIELDS +
        GLOBAL_ASSET_FIELDS in controllers/settings.py) may be removed.
        Anything else, e.g. credentials, is a deliberate no-op: those are
        cleared by saving an empty value, never by the reset endpoint.
        """
        if key not in ALLOWED_KEYS:
            return
        await self._db.execute("DELETE FROM app_settings WHERE key = ?", (key,))

    async def save_global_values(self, values: dict[str, str]) -> dict[str, str]:
        """Persist global settings in one batch; returns {field: error} for rejected ones."""
        allowed = ALLOWED_KEYS | CREDENTIAL_KEYS
        rejected: dict[str, str] = {}
        for key, value in values.items():
            if key not in allowed:
                rejected[key] = f"{key!r} is not a valid global setting"
            else:
                error = _validate(key, value)
                if error is not None:
                    rejected[key] = error
        if rejected:
            return rejected
        for key, value in values.items():
            await self._persist(key, value)
        return {}

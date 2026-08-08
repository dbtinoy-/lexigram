import os
from html import escape
from pathlib import Path

from lexigram.ai.llm.routing.config import LLMConfig
from lexigram.ui import el, render_to_string
from lexigram.web import Controller, HTMLContent, get
from markupsafe import Markup

from shorts_creator.models.project_profile import (
    SUPPORTED_CAPTION_STYLES,
    ProfileSource,
    ResolvedSetting,
)
from shorts_creator.services.asset_service import AssetService
from shorts_creator.services.core import AppConfig
from shorts_creator.services.settings_store import SettingsStore
from shorts_creator.ui.button import ActionButton
from shorts_creator.ui.components.provider_card import ProviderCard
from shorts_creator.ui.components.settings_profile import (
    INPUT_CLASSES,
    _number_input,
    profile_field,
)
from shorts_creator.ui.shell import AppLayout

PROJECT_ROOT = Path(__file__).resolve().parents[3]

CREATIVE_FIELDS = (
    ("default_duration", "Default Duration (seconds)"),
    ("default_caption_style", "Default caption style"),
)

GLOBAL_ASSET_FIELDS = (
    ("asset_default_music_id", "Default Music", "music", ""),
    ("asset_default_font_id", "Default Font", "font", ""),
    ("asset_default_watermark_id", "Default Watermark", "watermark", ""),
    ("asset_default_bg_clip_id", "Default Background Clip", "clip", "background"),
    ("asset_default_outro_clip_id", "Default Outro Clip", "clip", "outro"),
)


def _global_setting(overrides: dict, key: str, config: AppConfig) -> ResolvedSetting:
    if key in overrides and overrides[key] != "":
        value = overrides[key]
        source = ProfileSource.GLOBAL
        is_overridden = True
    else:
        value = _builtin_fallback(key, config)
        source = ProfileSource.BUILT_IN
        is_overridden = False
    return ResolvedSetting(value=value, source=source, is_overridden=is_overridden)


def _builtin_fallback(key: str, config: AppConfig):
    if key == "default_duration":
        return str(config.default_duration)
    if key == "default_caption_style":
        return "highlight"
    return ""


def _text_input(key: str, value) -> str:
    return (
        f'<input type="text" id="{escape(key)}" name="{escape(key)}" '
        f'value="{escape(str(value))}" class="{INPUT_CLASSES}">'
    )


def _select_input(key: str, value, options: tuple) -> str:
    opts = "".join(
        f'<option value="{escape(o)}"{" selected" if o == value else ""}>{escape(o)}</option>'
        for o in options
    )
    return (
        f'<select id="{escape(key)}" name="{escape(key)}" class="{INPUT_CLASSES}">{opts}</select>'
    )


def _asset_select(key: str, assets, current: str) -> str:
    options = '<option value="">None (built-in)</option>'
    options += "".join(
        f'<option value="{escape(a.id)}"{" selected" if a.id == current else ""}>{escape(a.name)}</option>'
        for a in assets
    )
    return f'<select id="{escape(key)}" name="{escape(key)}" class="{INPUT_CLASSES}">{options}</select>'


def _secret_input(key: str, value, placeholder: str) -> str:
    return (
        f'<input type="password" id="{escape(key)}" name="{escape(key)}" '
        f'value="{escape(str(value))}" placeholder="{escape(placeholder)}" '
        f'autocomplete="new-password" class="{INPUT_CLASSES}">'
    )


def render_stock_provider_fields(overrides: dict[str, str]) -> str:
    """Pexels/Pixabay key fields; remembers env-configured keys as read-only
    placeholders so users see what actually applies.

    Shared by the /settings page and the refreshed fragment returned by
    /api/settings/save, mirroring render_global_creative_fields.
    """
    blocks = []
    for key, label, env_name in (
        ("pexels_api_key", "Pexels API key", "PEXELS_API_KEY"),
        ("pixabay_api_key", "Pixabay API key", "PIXABAY_API_KEY"),
    ):
        stored = overrides.get(key, "")
        env_value = os.environ.get(env_name) if not stored else ""
        if stored:
            badge, hint = (
                ("Configured", "bg-success/70 text-success border border-success/40"),
                ("Stored in app settings and used for automatic background footage."),
            )
        elif env_value:
            badge, hint = (
                ("Via env", "bg-warning/70 text-warning border border-warning/40"),
                (f"Falls back to the {env_name} environment variable."),
            )
        else:
            badge, hint = (
                ("Not configured", "bg-secondary/70 text-muted-foreground border border-border/40"),
                ("Used for automatic background footage when no clip is chosen."),
            )
        placeholder = "Set via environment" if env_value else "Paste your key"
        blocks.append(
            f'<div data-profile-field="{escape(key)}" id="profile-field-{escape(key)}" class="mb-4">'
            f'<label for="{escape(key)}" class="block text-foreground text-xs font-semibold mb-1.5">{escape(label)}</label>'
            f"{_secret_input(key, stored, placeholder)}"
            f'<p class="text-[11px] text-muted-foreground mt-1">{escape(hint)}</p>'
            f'<div class="flex items-center gap-1.5 mt-1.5">'
            f'<span class="inline-block text-[10px] font-mono px-1.5 py-0.5 rounded {badge[1]}">{badge[0]}</span>'
            f"</div></div>"
        )
    return "".join(blocks)


async def render_global_creative_fields(
    config: AppConfig,
    overrides: dict[str, str],
    asset_service: AssetService | None = None,
) -> str:
    """Creative field blocks for the global settings surface.

    Shared by the /settings page and the refreshed fragment returned by
    /api/settings/save, so both render the same controls and error slots.
    """
    blocks = []
    for key, label in CREATIVE_FIELDS:
        setting = _global_setting(overrides, key, config)
        if key == "default_caption_style":
            blocks.append(
                profile_field(
                    key,
                    label,
                    setting,
                    _select_input(key, setting.value, SUPPORTED_CAPTION_STYLES),
                    reset_url="/api/settings/reset-override",
                )
            )
        elif key == "default_duration":
            blocks.append(
                profile_field(
                    key,
                    label,
                    setting,
                    _number_input(key, setting.value),
                    reset_url="/api/settings/reset-override",
                )
            )
        else:
            blocks.append(
                profile_field(
                    key,
                    label,
                    setting,
                    _text_input(key, setting.value),
                    reset_url="/api/settings/reset-override",
                )
            )
    for key, label, asset_type, role in GLOBAL_ASSET_FIELDS:
        assets = await asset_service.list_by_type(asset_type, role or None) if asset_service else []
        setting = _global_setting(overrides, key, config)
        selector = _asset_select(key, assets, overrides.get(key, ""))
        blocks.append(
            profile_field(
                key,
                label,
                setting,
                selector,
                reset_url="/api/settings/reset-override",
            )
        )
    return "".join(blocks)


class SettingsController(Controller):
    def __init__(
        self, config: AppConfig, store: SettingsStore, asset_service: AssetService | None = None
    ):
        self.layout = AppLayout()
        self.config = config
        self.store = store
        self.asset_service = asset_service
        self.llm_config = LLMConfig.from_yaml(
            str(PROJECT_ROOT / "application.yaml"),
            profile=os.environ.get("LEX_PROFILE"),
            section="ai_llm",
        )

    @get("/settings")
    async def view_settings(self, request=None) -> HTMLContent:
        overrides = await self.store.get_overrides()
        profile = os.environ.get("LEX_PROFILE", "dev")

        is_htmx = bool(getattr(request, "headers", {}).get("HX-Request") == "true")

        providers_html = (
            "".join(
                ProviderCard(
                    {
                        "name": p.name,
                        "model": p.model,
                        "enabled": p.enabled,
                        "status": "healthy"
                        if (p.enabled and (p.base_url or bool(p.api_key)))
                        else "unconfigured"
                        if p.enabled
                        else "disabled",
                    }
                )
                for p in self.llm_config.providers
            )
            if self.llm_config.providers
            else el(
                "p",
                "No providers configured in application.yaml",
                class_="text-muted-foreground text-xs italic",
            )
        )

        creative_fields = await render_global_creative_fields(
            self.config, overrides, self.asset_service
        )
        stock_fields = render_stock_provider_fields(overrides)

        creative_card = el(
            "div",
            el(
                "h2",
                "Creative Defaults",
                class_="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3 font-mono",
            ),
            el(
                "div",
                el("span", "Video Size", class_="text-foreground text-xs font-semibold"),
                el(
                    "div",
                    el(
                        "span",
                        f"{self.config.reel_width}x{self.config.reel_height}",
                        class_="text-xs font-mono text-muted-foreground",
                    ),
                    el(
                        "span",
                        "Global Default",
                        class_="text-[10px] font-mono px-1.5 py-0.5 rounded bg-warning/70 text-warning border border-warning/40 ml-2",
                    ),
                    class_="flex items-center gap-2",
                ),
                class_="flex items-center justify-between py-2.5 border-b border-border/40 mb-3.5",
            ),
            el(
                "form",
                el(
                    "h3",
                    "Stock Video Providers (Pexels / Pixabay)",
                    class_="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-1 font-mono",
                ),
                el(
                    "p",
                    "Keys for automatic background footage. Saved keys override environment variables; clearing a field restores the env fallback.",
                    class_="text-[11px] text-muted-foreground mb-3",
                ),
                el("div", Markup(stock_fields), id="settings-stock-fields", class_="mb-6"),
                el(
                    "h3",
                    "Creative Defaults",
                    class_="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3 font-mono",
                ),
                el("div", Markup(creative_fields), id="settings-creative-fields"),
                ActionButton(
                    "Save Settings",
                    hx_post="/api/settings/save",
                    hx_target="#save-msg",
                    hx_swap="innerHTML",
                    class_extra="mt-3",
                ),
                id="settings-form",
            ),
            el("div", id="save-msg", class_="mt-2"),
            class_="bg-card/40 border border-border/60 rounded-xl p-5",
        )

        providers_card = el(
            "div",
            el(
                "h2",
                "LLM Providers & Health Router",
                class_="text-sm font-semibold uppercase tracking-wider text-muted-foreground mb-3 font-mono",
            ),
            el("div", providers_html, id="provider-list"),
            el(
                "div",
                el(
                    "button",
                    "Test All Connections",
                    hx_get="/api/health/providers/html",
                    hx_target="#provider-list",
                    hx_swap="innerHTML",
                    class_="bg-success hover:bg-success text-success-foreground px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all shadow-sm cursor-pointer",
                ),
                class_="mt-3 flex items-center gap-2",
            ),
            el(
                "div",
                el(
                    "h3",
                    "Config Summary",
                    class_="text-sm font-semibold uppercase tracking-wider text-muted-foreground mt-8 mb-3 font-mono",
                ),
                el(
                    "div",
                    el("span", "Active Profile", class_="text-foreground text-xs font-semibold"),
                    el("span", profile, class_="text-xs font-mono text-muted-foreground"),
                    class_="flex items-center justify-between py-2.5 border-b border-border/40",
                ),
                el(
                    "div",
                    el(
                        "span",
                        "Configured Providers",
                        class_="text-foreground text-xs font-semibold",
                    ),
                    el(
                        "span",
                        str(len(self.llm_config.providers)),
                        class_="text-xs font-mono text-muted-foreground",
                    ),
                    class_="flex items-center justify-between py-2.5 border-b border-border/40",
                ),
                el(
                    "div",
                    el("span", "Routing Strategy", class_="text-foreground text-xs font-semibold"),
                    el(
                        "span",
                        self.llm_config.strategy,
                        class_="text-xs font-mono text-muted-foreground",
                    ),
                    class_="flex items-center justify-between py-2.5 border-b border-border/40",
                ),
                class_="space-y-4",
            ),
            class_="bg-card/40 border border-border/60 rounded-xl p-5",
        )

        advanced_rows = [
            ("Caption font size / highlight styling", "src/shorts_creator/pipeline/pipeline.py"),
            ("Hook text sizing", "src/shorts_creator/pipeline/pipeline.py"),
            ("Whisper model", "src/shorts_creator/pipeline/narration.py"),
            ("Stock-video retry backoff", "src/shorts_creator/pipeline/stock_video.py"),
        ]
        advanced_section = el(
            "details",
            el(
                "summary",
                "\u25b8 Advanced",
                class_="text-sm font-semibold uppercase tracking-wider text-muted-foreground font-mono cursor-pointer select-none",
            ),
            el(
                "div",
                *(
                    el(
                        "div",
                        el("span", label, class_="text-foreground text-xs"),
                        el("span", path, class_="text-muted-foreground text-[11px] font-mono"),
                        class_="flex items-center justify-between py-2 border-b border-border/40",
                    )
                    for label, path in advanced_rows
                ),
                el(
                    "p",
                    "Global-only controls \u2014 project and topic profiles cannot override these. "
                    "Not yet editable from the UI \u2014 edit these files directly, then restart the app.",
                    class_="text-muted-foreground text-[11px] italic mt-2",
                ),
                class_="mt-3",
            ),
            class_="bg-card/40 border border-border/60 rounded-xl p-5",
        )

        tab_content = el(
            "div",
            creative_card,
            providers_card,
            advanced_section,
            class_="space-y-6",
        )

        if is_htmx:
            return HTMLContent(render_to_string(tab_content))

        content = render_to_string(
            el(
                "div",
                el(
                    "div",
                    el(
                        "h1",
                        "Settings & Provider Management",
                        class_="text-2xl font-bold text-foreground tracking-tight",
                    ),
                    el(
                        "p",
                        "Creative defaults, LLM provider router status, and global-only controls",
                        class_="text-muted-foreground text-xs mt-1 font-mono",
                    ),
                    class_="pb-4 border-b border-border/80",
                ),
                tab_content,
                class_="w-full space-y-6",
            )
        )
        html = self.layout.render(content=content, title="Settings", request=request)
        return HTMLContent(html)

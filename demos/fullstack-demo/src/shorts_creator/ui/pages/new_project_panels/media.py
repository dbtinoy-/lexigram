import json

from lexigram.ui import el

from shorts_creator.services.settings_store import PROVIDER_LABELS
from shorts_creator.ui.pages.new_project_overrides import _STAGE_LABELS, _WIDGET_DEFAULTS, _fmt_rank
from shorts_creator.ui.pages.new_project_panels.core import _panel


def _media_panel(
    asset_options: dict,
    current: dict | None = None,
    stages_json: str = "",
    stock_providers: list[str] | None = None,
    format_name: str | None = None,
    bg_mode: str = "",
):
    current = current or {}
    stock_providers = stock_providers or []
    stages_attrs = {"value": stages_json}
    if stages_json:
        stages_attrs["data_stages"] = stages_json

    stage_toggles = dict(_WIDGET_DEFAULTS["stages"])
    if stages_json:
        try:
            declared_stages = json.loads(stages_json)
        except (ValueError, TypeError):
            declared_stages = None
        if isinstance(declared_stages, dict):
            stage_toggles.update(declared_stages)
    if _fmt_rank(format_name):
        stage_toggles["music"] = True

    def picker(role: str, label: str, allow_url: bool = True, allow_api: bool = False):
        options = asset_options.get(role) or []
        selected = current.get(role)
        current_url = current.get(f"{role}_url") or "" if allow_url else ""
        source_value = current.get(f"{role}_source") or ""
        opts = [el("option", "Auto (default)", value="")]
        for a_id, name in options:
            attrs = {"value": a_id}
            if selected and str(a_id) == str(selected):
                attrs["selected"] = True
            opts.append(el("option", name, **attrs))
        url_attrs = {"value": current_url} if current_url else {}
        source_id = f"new-project-asset-{role}-source"
        asset_id = f"new-project-asset-{role}"
        url_id = f"new-project-asset-{role}-url"
        provider_id = f"new-project-asset-{role}-provider"
        if not allow_url and not allow_api:
            return [
                el(
                    "div",
                    el("label", label, class_="block text-[11px] text-muted-foreground mb-1"),
                    el(
                        "select",
                        *opts,
                        id=asset_id,
                        name=f"asset_{role}_id",
                        class_="w-full rounded-lg bg-secondary/80 border border-border px-3 py-1.5 text-xs text-foreground",
                    ),
                    class_="col-span-2",
                )
            ]
        source_opts = [el("option", "Assets", value="assets")]
        if allow_url:
            source_opts.append(
                el(
                    "option",
                    "Public URL",
                    value="url",
                    selected=source_value == "url" or (not source_value and bool(current_url)),
                )
            )
        if allow_api:
            source_opts.append(
                el("option", "Stock clip", value="api", selected=source_value == "api")
            )
        provider_select = None
        if allow_api:
            provider_opts = [el("option", "Auto", value="auto")]
            current_provider = current.get(f"{role}_provider") or ""
            for name in stock_providers:
                provider_opts.append(
                    el(
                        "option",
                        PROVIDER_LABELS.get(name, name.title()),
                        value=name,
                        selected=current_provider == name,
                    )
                )
            provider_select = el(
                "select",
                *provider_opts,
                id=provider_id,
                name=f"stock_provider_{role}",
                class_="w-40 flex-1 hidden rounded-lg bg-secondary/80 border border-border px-3 py-1.5 text-xs text-foreground",
            )
        return [
            el("label", label, class_="col-span-2 block text-[11px] text-muted-foreground"),
            el(
                "select",
                *source_opts,
                id=source_id,
                name=f"media_source_{role}",
                class_="w-32 rounded-lg bg-secondary/80 border border-border px-3 py-1.5 text-xs text-foreground",
                onchange="toggleMediaSource(this)",
            ),
            el(
                "div",
                el(
                    "select",
                    *opts,
                    id=asset_id,
                    name=f"asset_{role}_id",
                    class_="w-full flex-1 rounded-lg bg-secondary/80 border border-border px-3 py-1.5 text-xs text-foreground",
                ),
                el(
                    "input",
                    type="url",
                    id=url_id,
                    name=f"media_url_{role}",
                    placeholder="https://...  (public MP3/MP4 link)",
                    class_="w-full flex-1 hidden rounded-lg bg-secondary/80 border border-border px-3 py-1.5 text-xs text-foreground placeholder:text-muted-foreground/60",
                    **url_attrs,
                ),
                *([provider_select] if provider_select is not None else []),
                class_="flex items-center gap-2",
            ),
        ]

    bg_mode_value = "image" if bg_mode == "image" else "video"
    bg_mode_control = el(
        "div",
        el("label", "Background", class_="block text-[11px] text-muted-foreground mb-1"),
        el(
            "div",
            el(
                "label",
                el(
                    "input",
                    type="radio",
                    name="bg_mode",
                    value="video",
                    checked=bg_mode_value == "video",
                    onchange="toggleBgMode(this)",
                    class_="accent-primary",
                ),
                el("span", "Video", class_="text-xs text-foreground"),
                class_="flex items-center gap-1.5 cursor-pointer",
            ),
            el(
                "label",
                el(
                    "input",
                    type="radio",
                    name="bg_mode",
                    value="image",
                    checked=bg_mode_value == "image",
                    onchange="toggleBgMode(this)",
                    class_="accent-primary",
                ),
                el("span", "Image", class_="text-xs text-foreground"),
                class_="flex items-center gap-1.5 cursor-pointer",
            ),
            class_="flex items-center gap-4",
        ),
        class_="mb-3",
    )

    return _panel(
        "Media & extras — background, music, outro, watermark",
        el(
            "div",
            bg_mode_control,
            el(
                "div",
                *picker(
                    "bg_clip",
                    "Background image" if bg_mode_value == "image" else "Background clip",
                    allow_api=bg_mode_value != "image",
                ),
                *picker("music", "Music track"),
                *picker("outro_clip", "Outro clip"),
                *picker("watermark", "Watermark image"),
                *picker("font", "Font", allow_url=False),
                id="bg-clip-picker-wrapper",
                class_="grid grid-cols-[max-content_1fr] gap-x-3 gap-y-2 items-center",
            ),
            el("label", "Include in reel", class_="block text-[11px] text-muted-foreground mb-1"),
            el(
                "div",
                *[
                    el(
                        "label",
                        el(
                            "input",
                            type="checkbox",
                            data_stage=key,
                            checked=on,
                            class_="accent-primary stage-toggle",
                        ),
                        el("span", _STAGE_LABELS[key], class_="text-xs text-foreground"),
                        class_="flex items-center gap-1.5 text-[11px] text-foreground",
                    )
                    for key, on in stage_toggles.items()
                ],
                id="new-project-stages",
                class_="flex flex-wrap gap-2",
            ),
            el("input", id="new-project-stages-json", type="hidden", name="stages", **stages_attrs),
            el(
                "script",
                """
                function toggleMediaSource(sel) {
                    var role = sel.id.replace('new-project-asset-', '').replace('-source', '');
                    var urlField = document.getElementById('new-project-asset-' + role + '-url');
                    var assetField = document.getElementById('new-project-asset-' + role);
                    var providerField = document.getElementById('new-project-asset-' + role + '-provider');
                    var isUrl = sel.value === 'url';
                    var isApi = sel.value === 'api';
                    if (urlField) {
                        urlField.classList.toggle('hidden', !isUrl);
                        urlField.disabled = !isUrl;
                    }
                    if (assetField) {
                        assetField.classList.toggle('hidden', isUrl || isApi);
                        assetField.disabled = isUrl || isApi;
                    }
                    if (providerField) {
                        providerField.classList.toggle('hidden', !isApi);
                        providerField.disabled = !isApi;
                    }
                }
                document.querySelectorAll('[id$="-source"]').forEach(toggleMediaSource);
                """,
            ),
            id="composer-media-panel",
        ),
        "composer-media-panel-wrapper",
    )

# Configuration

Complete reference of every configuration dataclass in `lexigram-ui`.

---

## UIConfig

```python
@dataclass
class UIConfig(BaseConfig):
    config_section = "ui"
```

Controls rendering defaults. Read from the `[ui]` section of `application.yaml` (or env vars prefixed with `LEX_UI__`).

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `default_theme` | `str` | `"default"` | Default CSS theme name passed to `shadcn_css()` |
| `auto_escape` | `bool` | `True` | HTML-escape user strings by default |
| `htmx_version` | `str` | `"2.0.4"` | HTMX CDN version |
| `debug_components` | `bool` | `False` | Render `data-component` debug attributes |
| `theme` | `str` | `"light"` | Active UI theme (`light`, `dark`, `system`) |
| `enable_sse` | `bool` | `False` | Enable Server-Sent Events support |
| `enable_realtime` | `bool` | `False` | Enable realtime update features |

### Methods

**`validate_for_environment(env: Environment) -> list[ConfigIssue]`**

Returns warnings for unsafe config in production (e.g., `debug_components=True`).

### Environment Variables

All fields are overridable via `LEX_UI__<FIELD>`:

```bash
LEX_UI__THEME=dark LEX_UI__ENABLE_SSE=true
```

---

## DebounceConfig

```python
@dataclass
class DebounceConfig:
    delay_ms: int = 300
    changed: bool = True
```

Generates HTMX trigger strings with debounce:

```python
DebounceConfig(delay_ms=500).to_trigger("input")
# → "input changed delay:500ms"
```

---

## HTMLDocumentConfig

```python
@dataclass
class HTMLDocumentConfig:
```

Controls the `<html>` document shell generation.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `lang` | `str` | `"en"` | HTML lang attribute |
| `charset` | `str` | `"UTF-8"` | Meta charset |
| `viewport` | `str` | `"width=device-width, initial-scale=1.0"` | Viewport meta tag |
| `description` | `str` | `""` | Meta description |
| `keywords` | `list[str]` | `[]` | Meta keywords |
| `author` | `str` | `""` | Meta author |
| `robots` | `str` | `""` | Robots directive (e.g., `"noindex, nofollow"`) |
| `favicon` | `str | None` | `None` | Favicon URL |
| `favicon_type` | `str` | `"image/x-icon"` | Favicon MIME type |
| `theme_color` | `str` | `"#ffffff"` | Theme color meta tag |
| `og_title` | `str` | `""` | Open Graph title |
| `og_description` | `str` | `""` | Open Graph description |
| `og_image` | `str` | `""` | Open Graph image URL |
| `og_url` | `str` | `""` | Open Graph URL |
| `og_type` | `str` | `"website"` | Open Graph type |
| `extra_head` | `str` | `""` | Additional raw HTML for `<head>` |

---

## BaseLayoutConfig

```python
@dataclass
class BaseLayoutConfig(HTMLDocumentConfig):
```

Extends `HTMLDocumentConfig` with layout settings.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `site_name` | `str` | `"Lexigram Admin"` | Site name for title suffix |
| `site_logo` | `str | None` | `None` | Logo URL |
| `site_logo_alt` | `str` | `"Logo"` | Logo alt text |
| `theme` | `str` | `"light"` | Active theme |
| `primary_color` | `str` | `"#6b7280"` | Primary brand color (overridden by CSS variables in ShadCN mode) |
| `accent_color` | `str` | `"#8b5cf6"` | Accent brand color |
| `htmx_enabled` | `bool` | `True` | Enable HTMX |
| `htmx_boost` | `bool` | `True` | Enable HTMX boost |
| `htmx_version` | `str` | `"1.9.10"` | HTMX version |
| `css_files` | `list[str]` | `[]` | Additional CSS URLs |
| `js_files` | `list[str]` | `[]` | Additional JS URLs |
| `include_alpine` | `bool` | `False` | Enable Alpine.js |
| `alpine_version` | `str` | `"3.x.x"` | Alpine.js version |

**Note:** `htmx_version` in `BaseLayoutConfig` defaults to `"1.9.10"` while `UIConfig` defaults to `"2.0.4"`. This is intentional — the layout uses v1 for legacy compatibility; the UI config targets v2.

---

## HeadConfig

```python
@dataclass
class HeadConfig:
```

Controls the `<head>` section rendering via `HeadRenderer`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `css_framework` | `str` | `"tailwind"` | CSS framework (`tailwind`, `pico`, `custom`) |
| `css_framework_url` | `str` | `""` | Custom CSS framework URL |
| `css_files` | `list[str]` | `[]` | Additional CSS file URLs |
| `inline_css` | `str` | `""` | Inline CSS rules |
| `icon_library` | `str` | `"lucide"` | Icon library (`lucide`, `heroicons`, `feather`) |
| `icon_library_url` | `str` | Lucide CDN | Icon library script URL |
| `font_url` | `str` | `""` | Google Fonts URL |
| `htmx_url` | `str` | HTMX CDN | HTMX script URL |
| `include_hyperscript` | `bool` | `False` | Include Hyperscript |
| `hyperscript_url` | `str` | Hyperscript CDN | Hyperscript script URL |

---

## FooterConfig

```python
@dataclass
class FooterConfig:
```

Controls footer rendering via `FooterRenderer`.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `show_copyright` | `bool` | `True` | Show copyright banner |
| `copyright_holder` | `str` | `""` | Copyright holder name |
| `copyright_start_year` | `int | None` | `None` | Start year for range display |
| `show_version` | `bool` | `True` | Show version number |
| `version` | `str` | `""` | Version string |
| `links` | `list[Any]` | `[]` | List of `FooterLink` objects |
| `sticky` | `bool` | `False` | Stick footer to viewport bottom |
| `show_divider` | `bool` | `True` | Show top divider |
| `custom_left` | `str` | `""` | Custom left section HTML |
| `custom_right` | `str` | `""` | Custom right section HTML |

---

## ToastConfig

```python
@dataclass
class ToastConfig:
```

Controls toast container behavior.

| Field | Type | Default | Description |
|-------|------|---------|-------------|
| `position` | `str` | `"top-right"` | Position (`top-right`, `top-left`, `bottom-right`, `bottom-left`) |
| `default_duration_ms` | `int` | `5000` | Default toast duration |
| `max_toasts` | `int` | `5` | Max visible toasts |
| `stack_direction` | `str` | `"down"` | Stack direction (`up` or `down`) |
| `listen_for_events` | `bool` | `True` | Listen for `showToast` events |
| `event_name` | `str` | `"showToast"` | Custom event name |
| `animation_in` | `str` | `"fade-in-right"` | Entrance animation class |
| `animation_out` | `str` | `"fade-out-right"` | Exit animation class |

---

## ShadCN CSS Variable Reference

When `default_theme="default"`, the layout generates CSS custom properties via `shadcn_css()`. These variables are available for use in your own components:

### Background & Text

| Variable | Light Default | Dark Default |
|----------|--------------|--------------|
| `--background` | `oklch(1 0 0)` | `oklch(0.145 0 0)` |
| `--foreground` | `oklch(0.145 0 0)` | `oklch(0.985 0 0)` |
| `--card` | `oklch(1 0 0)` | `oklch(0.205 0 0)` |
| `--card-foreground` | `oklch(0.145 0 0)` | `oklch(0.985 0 0)` |
| `--popover` | `oklch(1 0 0)` | `oklch(0.205 0 0)` |
| `--popover-foreground` | `oklch(0.145 0 0)` | `oklch(0.985 0 0)` |

### Interactive Colors

| Variable | Light | Dark |
|----------|-------|------|
| `--primary` | `oklch(0.205 0 0)` | `oklch(0.922 0 0)` |
| `--primary-foreground` | `oklch(0.985 0 0)` | `oklch(0.205 0 0)` |
| `--secondary` | `oklch(0.97 0 0)` | `oklch(0.269 0 0)` |
| `--secondary-foreground` | `oklch(0.205 0 0)` | `oklch(0.985 0 0)` |
| `--muted` | `oklch(0.97 0 0)` | `oklch(0.269 0 0)` |
| `--muted-foreground` | `oklch(0.556 0 0)` | `oklch(0.708 0 0)` |
| `--accent` | `oklch(0.97 0 0)` | `oklch(0.269 0 0)` |
| `--accent-foreground` | `oklch(0.205 0 0)` | `oklch(0.985 0 0)` |
| `--destructive` | `oklch(0.577 0.245 27.325)` | `oklch(0.704 0.191 22.216)` |
| `--destructive-foreground` | `oklch(1 0 0)` | `oklch(0.97 0 0)` |

### Borders & Rings

| Variable | Light | Dark |
|----------|-------|------|
| `--border` | `oklch(0.922 0 0)` | `oklch(1 0 0 / 10%)` |
| `--input` | `oklch(0.922 0 0)` | `oklch(1 0 0 / 15%)` |
| `--ring` | `oklch(0.708 0 0)` | `oklch(0.556 0 0)` |
| `--radius` | `0.625rem` | `0.625rem` |

### Chart Colors

| Variable | Light | Dark |
|----------|-------|------|
| `--chart-1` | `oklch(0.87 0 0)` | `oklch(0.87 0 0)` |
| `--chart-2` | `oklch(0.556 0 0)` | `oklch(0.556 0 0)` |
| `--chart-3` | `oklch(0.439 0 0)` | `oklch(0.439 0 0)` |
| `--chart-4` | `oklch(0.371 0 0)` | `oklch(0.371 0 0)` |
| `--chart-5` | `oklch(0.269 0 0)` | `oklch(0.269 0 0)` |

### Sidebar Colors

| Variable | Light | Dark |
|----------|-------|------|
| `--sidebar` | `oklch(0.985 0 0)` | `oklch(0.205 0 0)` |
| `--sidebar-foreground` | `oklch(0.145 0 0)` | `oklch(0.985 0 0)` |
| `--sidebar-primary` | `oklch(0.205 0 0)` | `oklch(0.488 0.243 264.376)` |
| `--sidebar-primary-foreground` | `oklch(0.985 0 0)` | `oklch(0.985 0 0)` |
| `--sidebar-accent` | `oklch(0.97 0 0)` | `oklch(0.269 0 0)` |
| `--sidebar-accent-foreground` | `oklch(0.205 0 0)` | `oklch(0.985 0 0)` |
| `--sidebar-border` | `oklch(0.922 0 0)` | `oklch(1 0 0 / 10%)` |
| `--sidebar-ring` | `oklch(0.708 0 0)` | `oklch(0.556 0 0)` |

### Status Colors

| Variable | Light | Dark |
|----------|-------|------|
| `--color-success` | `oklch(0.52 0.18 149.214)` | `oklch(0.76 0.14 149.214)` |
| `--color-success-foreground` | `oklch(1 0 0)` | `oklch(0.97 0 0)` |
| `--color-warning` | `oklch(0.795 0.184 86.047)` | `oklch(0.82 0.15 86.047)` |
| `--color-warning-foreground` | `oklch(0.145 0 0)` | `oklch(0.2 0 0)` |
| `--color-info` | `oklch(0.56 0.23 277.117)` | `oklch(0.74 0.135 277.116)` |
| `--color-info-foreground` | `oklch(1 0 0)` | `oklch(0.97 0 0)` |

### Gray Scale

Available as `--gray-50` through `--gray-950` for direct use in components.

### Utility Classes

The `render_utility_classes()` function produces classes like:
- `.bg-background`, `.bg-card`, `.bg-popover`, `.bg-muted`
- `.text-foreground`, `.text-muted-foreground`, `.text-card-foreground`
- `.border-border`, `.border-input`
- `.rounded-custom`

---

## CSP Requirements

The `UI_CSP_REQUIREMENTS` constant provides Content Security Policy directives:

```python
from lexigram.ui.constants import UI_CSP_REQUIREMENTS
```

Add these to your application's CSP headers when using lexigram-ui with external CDN assets (HTMX, Alpine.js, Lucide icons, Tailwind CDN).

---

## Loading Config

```mermaid
flowchart LR
    subgraph Sources[Config Sources]
        YAML[application.yaml<br/>ui: section]
        ENV[Environment variables<br/>LEX_UI__*]
        PyCall[Python API<br/>UIConfig(...)]
    end
    subgraph Merge[Merge & Validate]
        UC[UIConfig<br/>validate_for_environment]
    end
    subgraph DI[DI Registration]
        UP[UIProvider.register]
        CS[container.singleton<br/>UIConfig, config]
    end
    subgraph App[Application]
        Resolved[Resolved UIConfig<br/>available via container]
    end

    YAML --> UC
    ENV --> UC
    PyCall --> UC
    UC --> UP
    UP --> CS
    CS --> Resolved
```

Config is loaded from `application.yaml`:

```yaml
ui:
  default_theme: default
  theme: dark
  enable_sse: true
  debug_components: false
```

Or via environment variables:

```bash
export LEX_UI__THEME=dark
export LEX_UI__ENABLE_SSE=true
```

The `UIConfig` class supports `validate_for_environment()` which warns when `debug_components` is enabled in production.

During DI registration, `UIProvider.register()` calls `container.singleton(UIConfig, config)` so the resolved config instance is available throughout the application.

"""UIConfig — configuration model for the UI provider."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, ClassVar

from lexigram.config import BaseConfig
from lexigram.contracts.core.config import ConfigIssue, Environment
from lexigram.ui.constants import ENV_NESTED_DELIMITER, ENV_PREFIX
from lexigram.validation import ConfigDict, Field


@dataclass
class DebounceConfig:
    """Configuration for debounced HTMX triggers."""

    delay_ms: int = 300
    changed: bool = True

    def to_trigger(self, base_trigger: str = "input") -> str:
        """Generate HTMX trigger string with debounce."""
        parts = [base_trigger]
        if self.changed:
            parts.append("changed")
        parts.append(f"delay:{self.delay_ms}ms")
        return " ".join(parts)


@dataclass(init=False)
class UIConfig(BaseConfig):
    """Configuration for the lexigram-ui provider.

    These settings control rendering defaults and are read from the
    ``[ui]`` section of ``application.yaml`` (or equivalent config source).
    """

    config_section: ClassVar[str] = "ui"

    model_config: ClassVar[ConfigDict] = ConfigDict(
        env_prefix=ENV_PREFIX,  # type: ignore[typeddict-unknown-key]
        env_nested_delimiter=ENV_NESTED_DELIMITER,
        extra="ignore",
    )

    default_theme: str = Field(default="default", description="Default CSS theme name.")
    auto_escape: bool = Field(
        default=True, description="HTML-escape user strings by default."
    )
    htmx_version: str = Field(default="2.0.4", description="HTMX CDN version.")
    debug_components: bool = Field(
        default=False, description="Render data-component debug attributes."
    )
    theme: str = Field(default="light", description="Active UI theme.")
    enable_sse: bool = Field(
        default=False, description="Enable Server-Sent Events support."
    )
    enable_realtime: bool = Field(
        default=False, description="Enable realtime update features."
    )

    def validate_for_environment(
        self, env: Environment | None = None
    ) -> list[ConfigIssue]:
        """Check config is safe for the target environment."""
        issues: list[ConfigIssue] = []
        if env == Environment.PRODUCTION:
            if self.debug_components:
                issues.append(
                    ConfigIssue(
                        severity="warning",
                        field="debug_components",
                        message="Component debugging enabled in production",
                        suggestion="Set debug_components: false for performance",
                    )
                )
        return issues


@dataclass
class HTMLDocumentConfig:
    """Configuration for HTML document generation."""

    # Document basics
    lang: str = "en"
    charset: str = "UTF-8"

    # Meta tags
    viewport: str = "width=device-width, initial-scale=1.0"
    description: str = ""
    keywords: list[str] = field(default_factory=list)
    author: str = ""
    robots: str = ""  # e.g., "noindex, nofollow"

    # Favicon
    favicon: str | None = None
    favicon_type: str = "image/x-icon"

    # Theme
    theme_color: str = "#ffffff"

    # Open Graph
    og_title: str = ""
    og_description: str = ""
    og_image: str = ""
    og_url: str = ""
    og_type: str = "website"

    # Additional head content
    extra_head: str = ""


@dataclass
class BaseLayoutConfig(HTMLDocumentConfig):
    """Base configuration for all layouts.

    Extends HTMLDocumentConfig with common layout settings.
    """

    # Branding
    site_name: str = "Lexigram Admin"
    site_logo: str | None = None
    site_logo_alt: str = "Logo"

    # Theme
    theme: str = "light"
    primary_color: str = "#6b7280"
    accent_color: str = "#8b5cf6"

    # HTMX
    htmx_enabled: bool = True
    htmx_boost: bool = True
    htmx_version: str = "1.9.10"

    # External resources
    css_files: list[str] = field(default_factory=list)
    js_files: list[str] = field(default_factory=list)

    # Features
    include_alpine: bool = False
    alpine_version: str = "3.x.x"


@dataclass
class HeadConfig:
    """Configuration for head section."""

    # Default CSS framework
    css_framework: str = "tailwind"  # tailwind, pico, custom
    css_framework_url: str = ""

    # Custom CSS
    css_files: list[str] = field(default_factory=list)
    inline_css: str = ""

    # Icons
    icon_library: str = "lucide"  # lucide, heroicons, feather
    icon_library_url: str = "https://unpkg.com/lucide@0.263.1/dist/umd/lucide.min.js"

    # Fonts
    font_url: str = ""

    # HTMX
    htmx_url: str = "https://unpkg.com/htmx.org@1.9.10"
    include_hyperscript: bool = False
    hyperscript_url: str = "https://unpkg.com/hyperscript.org@0.9.12"


@dataclass
class FooterConfig:
    """Configuration for footer."""

    # Copyright
    show_copyright: bool = True
    copyright_holder: str = ""
    copyright_start_year: int | None = None

    # Version
    show_version: bool = True
    version: str = ""

    # Links
    links: list[Any] = field(default_factory=list)

    # Styling
    sticky: bool = False
    show_divider: bool = True

    # Custom content
    custom_left: str = ""
    custom_right: str = ""


@dataclass
class ToastConfig:
    """Configuration for toast container."""

    # Position
    position: str = "top-right"  # top-right, top-left, bottom-right, bottom-left

    # Behavior
    default_duration_ms: int = 5000
    max_toasts: int = 5
    stack_direction: str = "down"  # up or down

    # HTMX
    listen_for_events: bool = True
    event_name: str = "showToast"

    # Animation
    animation_in: str = "fade-in-right"
    animation_out: str = "fade-out-right"


__all__ = [
    "BaseLayoutConfig",
    "DebounceConfig",
    "FooterConfig",
    "HTMLDocumentConfig",
    "HeadConfig",
    "ToastConfig",
    "UIConfig",
]

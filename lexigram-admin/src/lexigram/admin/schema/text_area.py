from __future__ import annotations

from dataclasses import dataclass
import html as _html
from typing import Any

from lexigram.admin.schema.text import TextField
from lexigram.security.sanitization.html import sanitize_html
from lexigram.ui import Element, MarkdownEditor, RichEditor, TextArea, raw


def _sanitize_rich_text(value: str) -> str:
    """Sanitize rich-text HTML, escaping verbatim when nh3 is unavailable."""
    try:
        return sanitize_html(value)
    except ImportError:
        return _html.escape(value)


@dataclass(frozen=True, kw_only=True)
class TextAreaField(TextField):
    """A multi-line text input field.

    Renders a ``<textarea>`` form control. Column display truncates
    long content at 200 characters.
    """

    rows: int = 5

    def render_form(
        self, value: str | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {
            "name": self.name,
            "value": value if value is not None else "",
            "rows": self.rows,
        }
        if self.placeholder is not None:
            kwargs["placeholder"] = self.placeholder
        if self.label is not None:
            kwargs["label"] = self.label
        if errors:
            kwargs["error"] = errors[0]
        if self.readonly:
            kwargs["disabled"] = True
        return TextArea(**kwargs).render()

    def render_column(self, record: Any, value: str | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        if len(value) > 200:
            return Element("span", value[:200] + "...")
        return Element("span", value)


@dataclass(frozen=True, kw_only=True)
class MarkdownField(TextAreaField):
    """A markdown editor field with optional preview toggle.

    Renders a ``MarkdownEditor`` form control with Alpine.js-powered
    preview mode switching. Column display strips markdown syntax
    for plain-text preview.
    """

    preview: bool = True
    min_height: int = 300

    def render_form(
        self, value: str | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {
            "name": self.name,
            "value": value if value is not None else "",
            "rows": self.rows,
            "preview": self.preview,
            "min_height": self.min_height,
        }
        if self.placeholder is not None:
            kwargs["placeholder"] = self.placeholder
        if self.label is not None:
            kwargs["label"] = self.label
        if errors:
            kwargs["error"] = errors[0]
        if self.readonly:
            kwargs["disabled"] = True
        return MarkdownEditor(**kwargs).render()

    def render_column(self, record: Any, value: str | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        text = value
        text = text.replace("**", "").replace("__", "")
        text = text.replace("*", "").replace("_", "")
        text = text.replace("```", "").replace("`", "")
        text = text.replace("#", "")
        text = text.replace("> ", "")
        text = text.replace("[", "").replace("]", "")
        text = text.replace("(", "").replace(")", "")
        return Element("span", text.strip())


@dataclass(frozen=True, kw_only=True)
class RichTextField(TextAreaField):
    """A WYSIWYG rich-text field.

    Renders a ``RichEditor`` form control backed by Trix.js.
    Column display renders the HTML value as trusted (unescaped)
    content.

    Use ``render_assets()`` to include the required Trix.js CSS and
    JS when this field appears on a page.
    """

    toolbar: str | None = None
    min_height: int = 300

    _trix_css_url: str = "https://unpkg.com/trix@2.0.8/dist/trix.css"
    _trix_js_url: str = "https://unpkg.com/trix@2.0.8/dist/trix.umd.min.js"

    @classmethod
    def render_assets(cls) -> Element:
        """Render the Trix.js CSS and  ``<script>`` tags.

        Include the result in ``<head>`` once per page to enable
        RichEditor instances.
        """
        return Element(
            "div",
            Element(
                "link",
                rel="stylesheet",
                href=cls._trix_css_url,
            ),
            Element(
                "script",
                src=cls._trix_js_url,
                defer="",
            ),
        )

    def render_form(
        self, value: str | None, *, errors: list[str] | None = None
    ) -> Element:
        kwargs: dict[str, Any] = {
            "name": self.name,
            "value": value if value is not None else "",
            "min_height": self.min_height,
        }
        if self.placeholder is not None:
            kwargs["placeholder"] = self.placeholder
        if self.label is not None:
            kwargs["label"] = self.label
        if self.toolbar is not None:
            kwargs["toolbar"] = self.toolbar
        if errors:
            kwargs["error"] = errors[0]
        if self.readonly:
            kwargs["disabled"] = True
        return RichEditor(**kwargs).render()

    def render_column(self, record: Any, value: str | None) -> Element:
        if value is None:
            return Element("span", "\u2014", class_="text-muted")
        return Element("div", raw(_sanitize_rich_text(value)))

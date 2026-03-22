from __future__ import annotations

from typing import Any

from lexigram.ui.core.base import Component, el


class RichEditor(Component):
    """
    WYSIWYG editor using Trix.
    Requires Trix JS/CSS to be loaded in the page.
    """

    def __init__(
        self,
        name: str,
        value: str | None = None,
        label: str | None = None,
        placeholder: str | None = None,
        error: str | None = None,
        disabled: bool = False,
        required: bool = False,
        min_height: int = 300,
        toolbar: str | None = None,
        **props,
    ) -> None:
        super().__init__(
            name=name,
            value=value,
            label=label,
            placeholder=placeholder,
            error=error,
            disabled=disabled,
            required=required,
            min_height=min_height,
            toolbar=toolbar,
            **props,
        )
        self.name = name
        self.value = value or ""
        self.label = label
        self.placeholder = placeholder
        self.error = error
        self.disabled = disabled
        self.required = required
        self.min_height = min_height
        self.toolbar = toolbar

    def render(self) -> Any:
        # Trix uses a hidden input and a trix-editor element
        input_el = el(
            "input",
            type="hidden",
            name=self.name,
            id=f"{self.name}_input",
            value=self.value,
        )

        editor_classes = (
            "block w-full rounded-lg border-0 py-2 px-3 shadow-sm ring-1 ring-inset "
            "ring-[var(--input)] bg-background "
            "text-foreground prose dark:prose-invert max-w-none "
            "focus:ring-2 focus:ring-ring"
        )

        editor_kwargs: dict[str, Any] = {
            "input": f"{self.name}_input",
            "placeholder": self.placeholder,
            "class_": editor_classes,
            "disabled": "" if self.disabled else None,
            "style": f"min-height: {self.min_height}px",
            "role": "textbox",
            "aria-multiline": "true",
            "aria-labelledby": f"{self.name}-label" if self.label else None,
        }
        if self.toolbar is not None:
            editor_kwargs["data-toolbar"] = self.toolbar
        editor_el = el("trix-editor", **editor_kwargs)

        content = el("div", input_el, editor_el)

        if self.label:
            return el(
                "div",
                el(
                    "label",
                    self.label,
                    for_=f"{self.name}_input",
                    id=f"{self.name}-label",
                    class_="block text-sm font-medium text-foreground opacity-70 mb-1",
                ),
                content,
                (
                    el(
                        "p",
                        self.error,
                        id=f"{self.name}-error",
                        class_="mt-2 text-sm text-destructive",
                    )
                    if self.error
                    else ""
                ),
                class_="mb-4",
            )

        return content


class MarkdownEditor(Component):
    """
    Markdown editor with optional preview toggle.
    Uses Alpine.js for client-side preview mode switching.
    """

    def __init__(
        self,
        name: str,
        value: str | None = None,
        label: str | None = None,
        placeholder: str | None = None,
        error: str | None = None,
        rows: int = 10,
        disabled: bool = False,
        preview: bool = True,
        min_height: int = 300,
        **props,
    ) -> None:
        super().__init__(
            name=name,
            value=value,
            label=label,
            placeholder=placeholder,
            error=error,
            rows=rows,
            disabled=disabled,
            preview=preview,
            min_height=min_height,
            **props,
        )
        self.name = name
        self.value = value or ""
        self.label = label
        self.placeholder = placeholder
        self.error = error
        self.rows = rows
        self.disabled = disabled
        self.preview = preview
        self.min_height = min_height

    def render(self) -> Any:
        textarea_classes = (
            "block w-full rounded-lg border-0 py-2 px-3 shadow-sm ring-1 "
            "ring-inset focus:ring-2 focus:ring-inset sm:text-sm transition-all "
            "duration-200 bg-background text-foreground "
            "placeholder:text-muted-foreground font-mono "
            f"{'ring-destructive/40 focus:ring-destructive' if self.error else 'ring-[var(--input)] focus:ring-ring'}"
            f"{' opacity-50' if self.disabled else ''}"
        )

        escaped_value = self.value.replace("\\", "\\\\").replace("'", "\\'")

        x_data = (
            "{ mode: 'edit', get rendered() { "
            "const el = document.createElement('div'); "
            "el.textContent = this.$refs.textarea.value || ''; "
            "return el.innerHTML.replace(/\\n/g, '<br>'); } }"
        )

        textarea_el = el(
            "textarea",
            self.value,
            name=self.name,
            id=self.name,
            rows=self.rows,
            placeholder=self.placeholder,
            disabled=self.disabled,
            **{
                "x-ref": "textarea",
                "x-model": "mode === 'edit' ? undefined : undefined",
            },
            class_=textarea_classes,
            style=f"min-height: {self.min_height}px",
        )

        preview_el = el(
            "div",
            **{"x-show": "mode === 'preview'", "x-html": "rendered"},
            class_=(
                "prose dark:prose-invert max-w-none p-3 rounded-lg border "
                "border-border bg-background "
                f"min-h-[{self.min_height}px]"
            ),
        )

        toggle_btn = el(
            "button",
            type="button",
            **{
                "@click": "mode = mode === 'edit' ? 'preview' : 'edit'",
                "x-text": "mode === 'edit' ? 'Preview' : 'Edit'",
            },
            class_=(
                "text-xs font-medium px-2.5 py-1 rounded-md transition-colors duration-200 "
                "text-muted-foreground "
                "hover:text-foreground "
                "hover:bg-accent"
            ),
        )

        editor_wrap = el(
            "div",
            textarea_el,
            preview_el,
            **{"x-show": "mode === 'edit'", "x-cloak": ""},
        )

        header = (
            el(
                "div",
                toggle_btn,
                class_="flex items-center justify-end mb-1",
            )
            if self.preview
            else ""
        )

        content = el(
            "div",
            header,
            editor_wrap,
            **{"x-data": x_data},
        )

        if self.label:
            return el(
                "div",
                el(
                    "label",
                    self.label,
                    for_=self.name,
                    class_="block text-sm font-medium text-foreground opacity-70 mb-1",
                ),
                content,
                (
                    el(
                        "p",
                        self.error,
                        id=f"{self.name}-error",
                        class_="mt-2 text-sm text-destructive",
                    )
                    if self.error
                    else ""
                ),
                class_="mb-4",
            )

        return content

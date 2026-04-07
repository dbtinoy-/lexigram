from __future__ import annotations

from typing import Any

from lexigram.ui.atoms.inputs.base import AbstractInput
from lexigram.ui.core.base import el


class FileUpload(AbstractInput):
    """
    Standard file upload component with preview.
    """

    def __init__(
        self,
        name: str,
        accept: str = "*",
        **kwargs,
    ) -> None:
        super().__init__(name=name, **kwargs)
        self.accept = accept

    def _render_input(self) -> Any:
        input_id = f"file_{self.name}"

        # Alpine state for preview
        x_data = f"{{ previewUrl: '{self.value if self.value else ''}', fileName: '', handleFile(e) {{ const file = e.target.files[0]; if(file) {{ this.fileName = file.name; if(file.type.startsWith('image/')) {{ this.previewUrl = URL.createObjectURL(file); }} else {{ this.previewUrl = ''; }} }} }} }}"

        preview = el(
            "div",
            el(
                "template",
                el(
                    "div",
                    el(
                        "img",
                        **{
                            ":src": "previewUrl",
                            "class": "h-20 w-20 object-cover rounded-lg border border-border",
                        },
                    ),
                    class_="mb-3",
                ),
                **{"x-if": "previewUrl"},
            ),
            el(
                "div",
                el(
                    "span",
                    **{"x-text": "fileName || 'No file selected'"},
                    class_="text-sm text-muted-foreground",
                ),
                class_="mt-1",
            ),
            class_="mb-3",
        )

        input_el = el(
            "input",
            type="file",
            name=self.name,
            id=input_id,
            accept=self.accept,
            disabled=self.disabled,
            class_="block w-full text-sm text-muted-foreground file:mr-4 file:py-2 file:px-4 file:rounded-full file:border-0 file:text-sm file:font-semibold file:bg-primary/10 file:text-primary hover:file:bg-primary/20 disabled:opacity-50",
            **{"@change": "handleFile"},
        )

        return el(
            "div",
            preview,
            input_el,
            class_="p-4 border-2 border-dashed border-input rounded-xl bg-muted hover:bg-accent transition-colors duration-200",
            **{"x-data": x_data},
        )

    def render(self) -> Any:
        content = self._render_input()

        if not self.label:
            return content

        return el(
            "div",
            el(
                "label",
                self.label,
                for_=f"file_{self.name}",
                class_="block text-sm font-medium text-foreground mb-2",
            ),
            content,
            self._render_error(),
            class_="mb-6",
        )


class MultiFileUpload(AbstractInput):
    """
    Premium multi-file upload with drag and drop.
    """

    def __init__(
        self,
        name: str,
        accept: str = "*",
        **kwargs,
    ) -> None:
        super().__init__(name=name, **kwargs)
        self.accept = accept

    def _render_input(self) -> Any:
        # Alpine state for multiple files
        x_data = (
            "{ "
            "files: [], "
            "dragging: false, "
            "handleFiles(e) { "
            "  const newFiles = Array.from(e.target.files || e.dataTransfer.files); "
            "  newFiles.forEach(file => { "
            "    const reader = new FileReader(); "
            "    reader.onload = (re) => { "
            "      this.files.push({ name: file.name, size: (file.size/1024).toFixed(1) + ' KB', type: file.type, preview: file.type.startsWith('image/') ? re.target.result : null }); "
            "    }; "
            "    reader.readAsDataURL(file); "
            "  }); "
            "}, "
            "removeFile(index) { this.files.splice(index, 1); }"
            " }"
        )

        drop_zone = el(
            "div",
            el(
                "div",
                el(
                    "svg",
                    el(
                        "path",
                        d="M7 16a4 4 0 01-.88-7.903A5 5 0 1115.9 6L16 6a5 5 0 011 9.9M15 13l-3-3m0 0l-3 3m3-3v12",
                        stroke_linecap="round",
                        stroke_linejoin="round",
                        stroke_width="2",
                    ),
                    class_="mx-auto h-12 w-12 text-muted-foreground",
                    fill="none",
                    viewBox="0 0 24 24",
                    stroke="currentColor",
                ),
                el(
                    "p",
                    "Click or drag files here to upload",
                    class_="mt-1 text-sm text-muted-foreground",
                ),
                el(
                    "p",
                    f"Accepted: {self.accept}",
                    class_="text-xs text-muted-foreground",
                ),
                class_="text-center",
            ),
            el(
                "input",
                type="file",
                name=f"{self.name}[]",
                multiple="multiple",
                accept=self.accept,
                class_="absolute inset-0 w-full h-full opacity-0 cursor-pointer",
                **{"@change": "handleFiles"},
            ),
            class_="relative border-2 border-dashed border-input rounded-xl p-8 transition-all duration-200",
            **{
                ":class": "{ 'border-ring bg-primary/10': dragging, 'bg-muted': !dragging }",
                "@dragover.prevent": "dragging = true",
                "@dragleave.prevent": "dragging = false",
                "@drop.prevent": "dragging = false; handleFiles($event)",
            },
        )

        file_list = el(
            "div",
            el(
                "template",
                el(
                    "div",
                    el(
                        "div",
                        el(
                            "template",
                            el(
                                "img",
                                **{
                                    ":src": "file.preview",
                                    "class": "h-10 w-10 object-cover rounded-md mr-3",
                                },
                            ),
                            **{"x-if": "file.preview"},
                        ),
                        el(
                            "div",
                            el(
                                "p",
                                **{"x-text": "file.name"},
                                class_="text-sm font-medium text-foreground truncate max-w-[200px]",
                            ),
                            el(
                                "p",
                                **{"x-text": "file.size"},
                                class_="text-xs text-muted-foreground",
                            ),
                        ),
                        class_="flex items-center",
                    ),
                    el(
                        "button",
                        el(
                            "svg",
                            el(
                                "path",
                                d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16",
                                stroke_linecap="round",
                                stroke_linejoin="round",
                                stroke_width="2",
                            ),
                            class_="w-4 h-4",
                            fill="none",
                            viewBox="0 0 24 24",
                            stroke="currentColor",
                        ),
                        type="button",
                        **{"@click": "removeFile(index)"},
                        class_="text-muted-foreground hover:text-destructive transition-colors",
                    ),
                    class_="flex items-center justify-between p-3 bg-background border border-border rounded-lg shadow-sm",
                ),
                **{"x-for": "(file, index) in files", ":key": "index"},
            ),
            class_="mt-4 space-y-2",
            **{"x-show": "files.length > 0"},
        )

        return el("div", drop_zone, file_list, class_="w-full", **{"x-data": x_data})

    def render(self) -> Any:
        content = self._render_input()

        if not self.label:
            return content

        return el(
            "div",
            el(
                "label",
                self.label,
                class_="block text-sm font-medium text-foreground mb-2",
            ),
            content,
            self._render_error(),
            class_="mb-6",
        )


class AvatarUpload(AbstractInput):
    """
    Specialized file upload for user avatars.
    """

    def _render_input(self) -> Any:
        input_id = f"avatar_{self.name}"
        default_avatar = "https://ui-avatars.com/api/?name=User&background=random"

        x_data = f"{{ previewUrl: '{self.value if self.value else default_avatar}', handleFile(e) {{ const file = e.target.files[0]; if(file && file.type.startsWith('image/')) {{ this.previewUrl = URL.createObjectURL(file); }} }} }}"

        return el(
            "div",
            el(
                "div",
                el(
                    "img",
                    **{
                        ":src": "previewUrl",
                        "class": "h-24 w-24 rounded-full object-cover border-4 border-background shadow-md",
                    },
                ),
                el(
                    "label",
                    el(
                        "svg",
                        el(
                            "path",
                            d="M3 9a2 2 0 012-2h.93a2 2 0 001.664-.89l.812-1.22A2 2 0 0110.07 4h3.86a2 2 0 011.664.89l.812 1.22A2 2 0 0018.07 7H19a2 2 0 012 2v9a2 2 0 01-2 2H5a2 2 0 01-2-2V9z",
                        ),
                        el("path", d="M15 13a3 3 0 11-6 0 3 3 0 016 0z"),
                        class_="w-4 h-4",
                        fill="none",
                        viewBox="0 0 24 24",
                        stroke="currentColor",
                    ),
                    for_=input_id,
                    class_="absolute bottom-0 right-0 p-2 bg-primary rounded-full text-primary-foreground hover:bg-primary/90 cursor-pointer shadow-lg transition-transform hover:scale-110",
                ),
                class_="relative inline-block",
            ),
            el(
                "input",
                type="file",
                name=self.name,
                id=input_id,
                accept="image/*",
                disabled=self.disabled,
                class_="hidden",
                **{"@change": "handleFile"},
            ),
            el(
                "div",
                el(
                    "p",
                    "Min size 256x256px. PNG or JPG.",
                    class_="text-xs text-muted-foreground mt-2",
                ),
                class_="ml-4",
            )
            if not self.label
            else "",
            class_="flex items-center",
            **{"x-data": x_data},
        )

    def render(self) -> Any:
        content = self._render_input()

        if not self.label:
            return content

        return el(
            "div",
            el(
                "label",
                self.label,
                class_="block text-sm font-medium text-foreground mb-2",
            ),
            content,
            self._render_error(),
            class_="mb-6",
        )

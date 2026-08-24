"""Static atom re-exports for the ``lexigram.ui`` public surface.

Type-checker only: the top-level package resolves names lazily via
``__getattr__`` at runtime, so these imports never execute eagerly.
"""

# File-level suppression: this module is an intentional lazy-re-export
# manifest — imports live under TYPE_CHECKING on purpose.
# ruff: noqa: TC004

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from lexigram.ui.atoms.badge import Badge
    from lexigram.ui.atoms.button import Button, SubmitButton
    from lexigram.ui.atoms.divider import Divider
    from lexigram.ui.atoms.editors import MarkdownEditor, RichEditor
    from lexigram.ui.atoms.fieldset import Fieldset
    from lexigram.ui.atoms.file_upload import FileUpload
    from lexigram.ui.atoms.icon import Icon
    from lexigram.ui.atoms.inputs import (
        AbstractInput,
        AvatarUpload,
        BelongsTo,
        Checkbox,
        CheckboxList,
        ColorPicker,
        DateInput,
        EmailInput,
        Hidden,
        Input,
        KeyValueField,
        LazySelect,
        MorphTo,
        MultiFileUpload,
        MultiSelect,
        NativeMultiSelect,
        NumberInput,
        PasswordInput,
        Radio,
        Rating,
        Select,
        Slider,
        TagsInput,
        TextArea,
        TextInput,
        TimePicker,
        Toggle,
    )
    from lexigram.ui.atoms.label import Label
    from lexigram.ui.atoms.layout import Aside, Col, Container, Grid, Row
    from lexigram.ui.atoms.link import Link
    from lexigram.ui.atoms.progress_bar import ProgressBar
    from lexigram.ui.atoms.skeleton import Skeleton
    from lexigram.ui.atoms.spinner import Spinner
    from lexigram.ui.atoms.switch import Switch
    from lexigram.ui.atoms.tooltip import Tooltip

    __all__ = (
        "Badge",
        "Button",
        "SubmitButton",
        "Divider",
        "MarkdownEditor",
        "RichEditor",
        "Fieldset",
        "FileUpload",
        "Icon",
        "AbstractInput",
        "AvatarUpload",
        "BelongsTo",
        "Checkbox",
        "CheckboxList",
        "ColorPicker",
        "DateInput",
        "EmailInput",
        "Hidden",
        "Input",
        "KeyValueField",
        "LazySelect",
        "MorphTo",
        "MultiFileUpload",
        "MultiSelect",
        "NativeMultiSelect",
        "NumberInput",
        "PasswordInput",
        "Radio",
        "Rating",
        "Select",
        "Slider",
        "TagsInput",
        "TextArea",
        "TextInput",
        "TimePicker",
        "Toggle",
        "Label",
        "Aside",
        "Col",
        "Container",
        "Grid",
        "Row",
        "Link",
        "ProgressBar",
        "Skeleton",
        "Spinner",
        "Switch",
        "Tooltip",
    )

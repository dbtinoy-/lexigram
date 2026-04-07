"""
Input components for admin UI.

All inputs inherit from AbstractInput for consistent styling.
"""

from __future__ import annotations

from lexigram.ui.atoms.inputs.base import AbstractInput
from lexigram.ui.atoms.inputs.date import DateInput
from lexigram.ui.atoms.inputs.file import (
    AvatarUpload,
    FileUpload,
    MultiFileUpload,
)
from lexigram.ui.atoms.inputs.numeric import NumberInput, Slider
from lexigram.ui.atoms.inputs.selection import (
    BelongsTo,
    CheckboxList,
    LazySelect,
    MorphTo,
    MultiSelect,
    NativeMultiSelect,
    Radio,
    Select,
)
from lexigram.ui.atoms.inputs.special import (
    ColorPicker,
    Hidden,
    KeyValueField,
    Rating,
    TagsInput,
    TimePicker,
)
from lexigram.ui.atoms.inputs.text import (
    EmailInput,
    Input,
    PasswordInput,
    TextArea,
    TextInput,
)
from lexigram.ui.atoms.inputs.toggle import Checkbox, Toggle

__all__ = [
    # Base
    "AbstractInput",
    "AvatarUpload",
    "BelongsTo",
    "Checkbox",
    "CheckboxList",
    # Special
    "ColorPicker",
    # Date/Time
    "DateInput",
    "EmailInput",
    # File
    "FileUpload",
    "Hidden",
    "Input",
    "KeyValueField",
    "LazySelect",
    "MorphTo",
    "MultiFileUpload",
    "MultiSelect",
    "NativeMultiSelect",
    # Numeric
    "NumberInput",
    "PasswordInput",
    "Radio",
    "Rating",
    # Selection
    "Select",
    "Slider",
    "TagsInput",
    "TextArea",
    # Text
    "TextInput",
    "TimePicker",
    # Toggle
    "Toggle",
]

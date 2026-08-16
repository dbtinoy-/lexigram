"""PipeProtocol system for parameter validation and transformation.

Pipes transform and validate input before it reaches the handler.
"""

from __future__ import annotations

from lexigram.web.pipes.builtin.file import (
    FileSizeValidationPipe,
    FileTypeValidationPipe,
)
from lexigram.web.pipes.builtin.parse import (
    ParseBoolPipe,
    ParseDatePipe,
    ParseIntPipe,
    ParseUUIDPipe,
)

# Built-in pipes
from lexigram.web.pipes.builtin.validation import ValidationPipe
from lexigram.web.pipes.decorators import use_pipes
from lexigram.web.pipes.pipeline import PipePipeline
from lexigram.web.protocols import (
    ParamMetadata,
    PipeProtocol,
)
from lexigram.web.types import PipeBase

__all__ = [
    "FileSizeValidationPipe",
    "FileTypeValidationPipe",
    # Protocols
    "ParamMetadata",
    "ParseBoolPipe",
    "ParseDatePipe",
    "ParseIntPipe",
    "ParseUUIDPipe",
    "PipeBase",
    # Pipeline
    "PipePipeline",
    "PipeProtocol",
    # Built-in pipes
    "ValidationPipe",
    "use_pipes",
]

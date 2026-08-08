from pathlib import Path

from shorts_creator.formats.base import FormatDefinition
from shorts_creator.formats.registry import FormatRegistry

__all__ = ["FormatDefinition", "FormatRegistry"]

_formats_dir = Path(__file__).resolve().parents[3] / "data" / "formats"

registry = FormatRegistry()
registry.load(_formats_dir)

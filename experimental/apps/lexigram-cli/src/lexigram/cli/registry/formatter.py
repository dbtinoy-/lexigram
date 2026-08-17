"""Formatter registry for output formatting.

This module provides a registry pattern for output formatters (JSON, YAML, table, etc).
"""

from __future__ import annotations

import abc
from dataclasses import dataclass
from typing import Any, ClassVar

from lexigram import serialization as json


@dataclass
class FormatOptions:
    """Options for formatting."""

    indent: int = 2
    sort_keys: bool = False
    color: bool = True


class OutputFormatter(abc.ABC):
    """Abstract base class for output formatters."""

    name: ClassVar[str]
    content_type: ClassVar[str]
    file_extension: ClassVar[str]

    @abc.abstractmethod
    def format(self, data: Any, options: FormatOptions | None = None) -> str:
        """Format data for output."""

    @abc.abstractmethod
    def parse(self, input_str: str) -> Any:
        """Parse input string into data."""


class JSONFormatter(OutputFormatter):
    """JSON output formatter."""

    name = "json"
    content_type = "application/json"
    file_extension = "json"

    def format(self, data: Any, options: FormatOptions | None = None) -> str:
        opts = options or FormatOptions()
        return json.dumps(
            data,
            indent=opts.indent,
            sort_keys=opts.sort_keys,
            default=str,
        ).decode("utf-8")

    def parse(self, input_str: str) -> Any:
        return json.loads(input_str)


class YAMLFormatter(OutputFormatter):
    """YAML output formatter."""

    name = "yaml"
    content_type = "application/x-yaml"
    file_extension = "yaml"

    def format(self, data: Any, options: FormatOptions | None = None) -> str:
        try:
            import yaml

            return yaml.dump(data, sort_keys=False, default_flow_style=False)
        except ImportError:
            return json.dumps(data, indent=2, default=str).decode("utf-8")

    def parse(self, input_str: str) -> Any:
        try:
            import yaml

            return yaml.safe_load(input_str)
        except ImportError:
            raise ValueError("PyYAML not installed") from None


class TableFormatter(OutputFormatter):
    """Table output formatter for terminal."""

    name = "table"
    content_type = "text/plain"
    file_extension = "txt"

    def format(self, data: Any, options: FormatOptions | None = None) -> str:
        if not isinstance(data, list) or not data:
            return str(data)

        if isinstance(data[0], dict):
            headers = list(data[0].keys())
            rows = [[row.get(h, "") for h in headers] for row in data]
            return self._format_table(headers, rows)
        if isinstance(data[0], (list, tuple)):
            return self._format_table([], data)

        return str(data)

    def _format_table(self, headers: list, rows: list) -> str:
        if not rows:
            return ""

        col_widths = []
        if headers:
            for _i, h in enumerate(headers):
                col_widths.append(len(str(h)))
        else:
            for row in rows:
                for i, cell in enumerate(row):
                    if i >= len(col_widths):
                        col_widths.append(0)
                    col_widths[i] = max(col_widths[i], len(str(cell)))

        lines = []
        if headers:
            header_line = " | ".join(
                str(h).ljust(col_widths[i]) for i, h in enumerate(headers)
            )
            lines.append(header_line)
            lines.append("-" * len(header_line))

        for row in rows:
            row_line = " | ".join(
                str(cell).ljust(col_widths[i]) for i, cell in enumerate(row)
            )
            lines.append(row_line)

        return "\n".join(lines)

    def parse(self, input_str: str) -> Any:
        raise NotImplementedError("Table parsing not supported")


class SimpleFormatter(OutputFormatter):
    """Simple key=value output formatter."""

    name = "simple"
    content_type = "text/plain"
    file_extension = "txt"

    def format(self, data: Any, options: FormatOptions | None = None) -> str:
        if isinstance(data, dict):
            lines = []
            for key, value in data.items():
                lines.append(f"{key}: {value}")
            return "\n".join(lines)
        if isinstance(data, list):
            return "\n".join(str(item) for item in data)
        return str(data)

    def parse(self, input_str: str) -> Any:
        result = {}
        for line in input_str.strip().split("\n"):
            if ":" in line:
                key, value = line.split(":", 1)
                result[key.strip()] = value.strip()
        return result


class FormatterRegistry:
    """Registry for output formatters.

    Provides a pluggable way to add new formatters.
    """

    _formatters: dict[str, OutputFormatter] = {}
    _initialized: bool = False

    @classmethod
    def register(cls, formatter: type[OutputFormatter]) -> None:
        """Register a formatter class."""
        instance = formatter()
        cls._formatters[formatter.name] = instance

    @classmethod
    def get(cls, name: str) -> OutputFormatter | None:
        """Get a formatter by name."""
        cls.register_defaults()
        return cls._formatters.get(name)

    @classmethod
    def get_all(cls) -> dict[str, OutputFormatter]:
        """Get all registered formatters."""
        cls.register_defaults()
        return cls._formatters.copy()

    @classmethod
    def get_choices(cls) -> list[str]:
        """Get list of available formatter names."""
        cls.register_defaults()
        return list(cls._formatters.keys())

    @classmethod
    def register_defaults(cls) -> None:
        """Initialize default formatters if not already done."""
        if not cls._initialized:
            cls.register(JSONFormatter)
            cls.register(YAMLFormatter)
            cls.register(TableFormatter)
            cls.register(SimpleFormatter)
            cls._initialized = True


def format_output(
    data: Any,
    format_name: str = "json",
    options: FormatOptions | None = None,
) -> str:
    """Format data using the specified formatter."""
    formatter = FormatterRegistry.get(format_name)
    if not formatter:
        raise ValueError(f"Unknown format: {format_name}")
    return formatter.format(data, options)


__all__ = [
    "FormatOptions",
    "FormatterRegistry",
    "JSONFormatter",
    "OutputFormatter",
    "SimpleFormatter",
    "TableFormatter",
    "YAMLFormatter",
    "format_output",
]

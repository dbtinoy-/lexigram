"""Template loaders for PromptService.

Three loaders are provided:

- :class:`DictPromptLoader` — load from an in-process Python dict (inline
  config or app-registered templates).
- :class:`DirectoryPromptLoader` — load all YAML/JSON files from a directory.
  Each file may contain one or more templates.
- The :class:`PromptLoaderProtocol` defines the interface for custom loaders.

YAML template format
--------------------
A single file may contain multiple templates under a top-level ``templates``
key, or a single template as the top-level document::

    # multi-template file
    templates:
      - name: wellness_check
        version: v1
        provider: anthropic
        required_variables: [pet_name, species]
        optional_defaults:
          breed: Unknown
        content: |
          Assess {pet_name} ({species}, {breed}).

    # single-template file (flat)
    name: greeting
    version: v1
    content: Hello, {name}!

Dict format
-----------
Pass a list of dicts, each matching the :class:`~lexigram.ai.prompt.service.models.PromptTemplate`
fields::

    loader = DictPromptLoader([
        {
            "name": "greeting",
            "version": "v1",
            "content": "Hello, {name}!",
            "required_variables": ["name"],
        },
    ])
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Protocol, runtime_checkable

from lexigram.ai.prompt.constants import DEFAULT_RENDER_FORMAT
from lexigram.ai.prompt.rendering.engine import RenderFormat
from lexigram.ai.prompt.service.models import LLMProvider, PromptTemplate
from lexigram.logging import get_logger
from lexigram.serialization import JSONDecodeError, loads

logger = get_logger(__name__)

_SUPPORTED_EXTENSIONS = frozenset({".yaml", ".yml", ".json"})


@runtime_checkable
class PromptLoaderProtocol(Protocol):
    """Interface for objects that supply :class:`~lexigram.ai.prompt.service.models.PromptTemplate` instances."""

    def load(self) -> list[PromptTemplate]:
        """Return all templates from this source.

        Raises:
            OSError: If a file cannot be read.
            ValueError: If a template document is malformed.
        """
        ...


def _dict_to_template(
    data: dict[str, Any], default_format: RenderFormat = DEFAULT_RENDER_FORMAT
) -> PromptTemplate:
    """Convert a raw dict (from YAML or inline config) to a :class:`PromptTemplate`.

    Raises:
        ValueError: If ``name``, ``version``, or ``content`` are missing,
                    or if ``format`` is not a valid
                    :class:`~lexigram.ai.prompt.rendering.engine.RenderFormat`
                    value.
    """
    missing = [k for k in ("name", "version", "content") if not data.get(k)]
    if missing:
        raise ValueError(
            f"PromptTemplate dict is missing required keys: {missing!r}. Got: {list(data.keys())!r}"
        )

    raw_provider = data.get("provider", LLMProvider.GENERIC)
    try:
        provider = LLMProvider(raw_provider)
    except ValueError:
        raise ValueError(
            f"Unknown provider {raw_provider!r}. "
            f"Valid values: {[p.value for p in LLMProvider]!r}"
        )

    raw_format = data.get("format", default_format)
    try:
        render_format = RenderFormat(raw_format)
    except ValueError:
        raise ValueError(
            f"Unknown render format {raw_format!r}. "
            f"Valid values: {[f.value for f in RenderFormat]!r}"
        )

    required_variables = tuple(data.get("required_variables") or [])
    optional_defaults: dict[str, Any] = dict(data.get("optional_defaults") or {})

    return PromptTemplate(
        name=str(data["name"]),
        version=str(data["version"]),
        content=str(data["content"]),
        format=render_format,
        provider=provider,
        required_variables=required_variables,
        optional_defaults=optional_defaults,
        description=str(data.get("description", "")),
        metadata=dict(data.get("metadata") or {}),
    )


def _parse_file_content(path: Path, text: str) -> list[dict[str, Any]]:
    """Parse YAML or JSON text into a list of raw template dicts."""
    if path.suffix.lower() == ".json":
        data = loads(text)
    else:
        try:
            import yaml
        except ImportError as exc:
            raise ImportError(
                f"PyYAML is required to load YAML prompt templates. "
                f"Install it: pip install pyyaml. File: {path}"
            ) from exc
        data = yaml.safe_load(text)

    if data is None:
        return []

    if isinstance(data, list):
        return [d for d in data if isinstance(d, dict)]

    if isinstance(data, dict):
        if "templates" in data and isinstance(data["templates"], list):
            return [d for d in data["templates"] if isinstance(d, dict)]
        # Single flat template document
        return [data]

    raise ValueError(f"Unexpected YAML/JSON root type in {path}: {type(data).__name__}")


class DictPromptLoader:
    """Load templates from an in-process Python list of dicts.

    Args:
        templates: List of raw template dicts (see module docstring for schema).
        default_format: Format applied to dicts that don't declare ``format``.
    """

    def __init__(
        self,
        templates: list[dict[str, Any]],
        default_format: RenderFormat = DEFAULT_RENDER_FORMAT,
    ) -> None:
        self._templates = templates
        self._default_format = default_format

    def load(self) -> list[PromptTemplate]:
        """Parse and return all templates.

        Raises:
            ValueError: If any dict is malformed.
        """
        result: list[PromptTemplate] = []
        for i, raw in enumerate(self._templates):
            try:
                result.append(_dict_to_template(raw, self._default_format))
            except ValueError as exc:
                raise ValueError(f"Invalid template at index {i}: {exc}") from exc
        return result


class DirectoryPromptLoader:
    """Load templates from all YAML/JSON files in a directory.

    Files are processed in sorted order. Files starting with ``.`` or ``_``
    are skipped.  Files that fail to parse emit a warning and are skipped
    (non-fatal), matching the behaviour of
    :class:`~lexigram.config.lib.sources.DirectoryConfigSource`.

    Args:
        directory: Path to the directory containing template files.
        default_format: Format applied to files that don't declare ``format``.
    """

    def __init__(
        self,
        directory: str | Path,
        default_format: RenderFormat = DEFAULT_RENDER_FORMAT,
    ) -> None:
        self._directory = Path(directory)
        self._default_format = default_format

    def load(self) -> list[PromptTemplate]:
        """Scan the directory and return all parsed templates.

        Raises:
            OSError: If the directory cannot be read.
        """
        if not self._directory.is_dir():
            logger.warning(
                "prompt_loader_directory_not_found",
                directory=str(self._directory),
            )
            return []

        result: list[PromptTemplate] = []
        for path in sorted(self._directory.iterdir()):
            if path.suffix.lower() not in _SUPPORTED_EXTENSIONS:
                continue
            if path.name.startswith((".", "_")):
                continue

            try:
                text = path.read_text(encoding="utf-8")
                raw_dicts = _parse_file_content(path, text)
                for raw in raw_dicts:
                    try:
                        result.append(_dict_to_template(raw, self._default_format))
                    except ValueError as exc:
                        logger.warning(
                            "prompt_loader_template_parse_error",
                            file=str(path),
                            error=str(exc),
                        )
            except (OSError, JSONDecodeError, ValueError) as exc:
                logger.warning(
                    "prompt_loader_file_error",
                    file=str(path),
                    error=str(exc),
                )

        logger.debug(
            "prompt_loader_directory_loaded",
            directory=str(self._directory),
            count=len(result),
        )
        return result


__all__ = [
    "DictPromptLoader",
    "DirectoryPromptLoader",
    "PromptLoaderProtocol",
]

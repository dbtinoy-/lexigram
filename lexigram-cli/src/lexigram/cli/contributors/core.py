"""Core CLI contributor that registers the built-in framework generators."""

from __future__ import annotations

from lexigram.cli.contributors.base import BaseCliContributor
from lexigram.contracts.cli.types import GeneratorDefinition


def _title_from_name(name: str) -> str:
    """Derive a human-readable title from a generator name."""
    words = name.replace("-", " ").replace("_", " ").split()
    return "Generate " + " ".join(word.capitalize() for word in words)


_CORE_GENERATOR_DATA: list[tuple[str, dict[str, str]]] = [
    (
        "provider",
        {
            "description": "Generate provider",
            "generator_path": "lexigram.cli.generators.provider:ProviderGenerator",
            "default_output_dir": "src/providers",
        },
    ),
    (
        "test",
        {
            "description": "Generate test",
            "generator_path": "lexigram.cli.generators.test:TestGenerator",
            "default_output_dir": "tests/unit",
        },
    ),
]

_GENERATOR_DEFINITIONS: list[GeneratorDefinition] = [
    GeneratorDefinition(
        name=name,
        title=_title_from_name(name),
        description=metadata["description"],
        contributor="core",
        generator_path=metadata["generator_path"],
        default_output_dir=metadata["default_output_dir"],
    )
    for name, metadata in _CORE_GENERATOR_DATA
]


class CoreCliContributor(BaseCliContributor):
    """CLI contributor that registers all built-in framework generators."""

    @property
    def contributor_id(self) -> str:
        return "core"

    def get_generators(self) -> list[GeneratorDefinition]:
        return list(_GENERATOR_DEFINITIONS)


__all__ = ["_CORE_GENERATOR_DATA", "CoreCliContributor"]

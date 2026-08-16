from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class GeneratorOption:
    """A single CLI option/flag accepted by a generator command.

    Used for auto-generated help text and input validation.
    """

    name: str
    type_hint: str  # e.g. "str", "bool", "int"
    required: bool = False
    default: object | None = None
    description: str = ""
    short_flag: str | None = None  # e.g. "-n"


@dataclass(frozen=True)
class GeneratorDefinition:
    """Describes a single executable scaffolding generator contributed to the CLI.

    Generators are discovered via ``CliContributorProtocol.get_generators()``
    and assembled into the unified ``gen`` command by ``CommandAssembler``.
    ``generator_path`` is required so every definition can be executed once it
    has been discovered and registered.
    """

    name: str
    title: str
    description: str
    contributor: str  # contributor_id of the owning contributor
    generator_path: str
    category: str = "general"
    options: tuple[GeneratorOption, ...] = field(default_factory=tuple)
    default_output_dir: str = "src"


__all__ = ["GeneratorDefinition", "GeneratorOption"]

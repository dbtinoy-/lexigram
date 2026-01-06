from __future__ import annotations

from lexigram.contracts.cli.contributions import (
    CommandContribution,
    DoctorCheckContribution,
    HealthCheckContribution,
    HookContribution,
    ShellContextContribution,
)
from lexigram.contracts.cli.generators import (
    GenerationResult,
    GeneratorProtocol,
)
from lexigram.contracts.cli.naming import to_camel_case, to_snake_case
from lexigram.contracts.cli.parsers import FieldSpec, parse_fields
from lexigram.contracts.cli.protocols import CliContributorProtocol
from lexigram.contracts.cli.types import GeneratorDefinition, GeneratorOption

__all__ = [
    "CliContributorProtocol",
    "CommandContribution",
    "DoctorCheckContribution",
    "FieldSpec",
    "GenerationResult",
    "GeneratorDefinition",
    "GeneratorOption",
    "GeneratorProtocol",
    "HealthCheckContribution",
    "HookContribution",
    "ShellContextContribution",
    "parse_fields",
    "to_camel_case",
    "to_snake_case",
]

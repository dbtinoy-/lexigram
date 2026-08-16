"""Resource generator for the web package."""

from __future__ import annotations

from pathlib import Path
from typing import Any

from lexigram.codegen import (
    GenerationResult,
    ModelGenerator,
    ServiceGenerator,
)
from lexigram.web.cli.generators.controller import ControllerGenerator


class ResourceGenerator:
    """Generate a model, service, and web controller slice."""

    name = "resource"
    description = "Generate resource"
    default_output_dir = "src"
    model_generator_class = ModelGenerator
    service_generator_class = ServiceGenerator
    controller_generator_class = ControllerGenerator

    def __init__(
        self,
        output_dir: str = "src",
        model_generator_class: type[Any] | None = None,
        service_generator_class: type[Any] | None = None,
    ) -> None:
        self.output_dir = Path(output_dir)
        if model_generator_class is not None:
            self.model_generator_class = model_generator_class
        if service_generator_class is not None:
            self.service_generator_class = service_generator_class

    def generate(
        self,
        name: str,
        *,
        dry_run: bool = False,
        force: bool = False,
        **kwargs: object,
    ) -> GenerationResult:
        fields_str = str(kwargs.get("fields_str", ""))
        model_result = self.model_generator_class(
            output_dir=self.output_dir / "models",
        ).generate(
            name,
            fields_str=fields_str,
            dry_run=dry_run,
            force=force,
        )
        service_result = self.service_generator_class(
            output_dir=self.output_dir / "services",
        ).generate(
            name,
            dry_run=dry_run,
            force=force,
        )
        controller_result = self.controller_generator_class(
            output_dir=self.output_dir / "controllers",
        ).generate(
            name,
            dry_run=dry_run,
            force=force,
        )
        return GenerationResult(
            files_created=(
                model_result.files_created
                + service_result.files_created
                + controller_result.files_created
            ),
            files_skipped=(
                model_result.files_skipped
                + service_result.files_skipped
                + controller_result.files_skipped
            ),
            files_overwritten=(
                model_result.files_overwritten
                + service_result.files_overwritten
                + controller_result.files_overwritten
            ),
        )


__all__ = ["ResourceGenerator"]

from pathlib import Path

from shorts_creator.contracts.errors import ContractLoadError
from shorts_creator.formats.base import FormatDefinition
from shorts_creator.formats.loader import is_contract_violation, load_format


class FormatRegistry:
    """Registry of presentation formats loaded from data/formats/*/FORMAT.md.

    ``load`` collects per-file failures: non-contract breakage (missing
    frontmatter, bad YAML, absent directory) is skipped and reported via
    ``errors()``; contract violations (unknown capability, unimplemented
    pipeline requirement, bad requires key) are also collected in boot mode
    (strict=False) but raise ``ContractLoadError`` in strict mode. The
    import-time singleton always uses boot mode so the app stays up and
    reports loudly; tests and authoring gates use strict mode to fail fast.
    """

    def __init__(self):
        self._formats: dict[str, FormatDefinition] = {}
        self._errors: list[tuple[Path, Exception]] = []

    def load(self, formats_dir: str | Path, strict: bool = False) -> int:
        count = 0
        self._errors = []
        failures: list[tuple[Path, Exception]] = []
        for md_path in Path(formats_dir).glob("*/FORMAT.md"):
            try:
                fmt = load_format(md_path)
                self._formats[fmt.name] = fmt
                count += 1
            except Exception as exc:  # noqa: BLE001 - classified below
                if is_contract_violation(exc):
                    failures.append((md_path, exc))
        if strict and failures:
            raise ContractLoadError(failures)
        self._errors = failures
        return count

    def errors(self) -> list[tuple[Path, Exception]]:
        """Per-file load failures from the most recent ``load`` call."""
        return list(self._errors)

    def get(self, name: str) -> FormatDefinition | None:
        return self._formats.get(name)

    @property
    def available(self) -> list[FormatDefinition]:
        return list(self._formats.values())

    def names(self) -> list[str]:
        return list(self._formats.keys())

    def has(self, name: str) -> bool:
        return name in self._formats

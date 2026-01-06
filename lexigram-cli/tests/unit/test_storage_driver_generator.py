"""Regression tests for the storage driver generator."""

from __future__ import annotations

from pathlib import Path

from lexigram.cli.registry.generator import GeneratorAdapter
from lexigram.storage.cli.generators.storage_driver import StorageDriverGenerator


class TestStorageDriverGenerator:
    """Verify storage driver generation stays aligned with storage backends."""

    def test_adapter_uses_backend_output_dir(self) -> None:
        adapter = GeneratorAdapter(StorageDriverGenerator, "src/storage/backends")
        assert adapter.get_default_output_dir() == "src/storage/backends"

    def test_generate_uses_backend_import_surface(self, tmp_path: Path) -> None:
        generator = StorageDriverGenerator(output_dir=str(tmp_path))
        result = generator.generate(
            "WidgetStorage", output_dir=str(tmp_path), force=True
        )
        generated_file = tmp_path / "widget_storage.py"

        assert result.files_created == [tmp_path]
        assert generated_file.exists()

        content = generated_file.read_text()
        assert (
            "from lexigram.storage.backends import AbstractDriver as BaseDriver"
            in content
        )

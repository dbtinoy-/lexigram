"""Tests for GeneratorBase output-dir resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from lexigram.codegen.base import GeneratorBase


class _StubGenerator(GeneratorBase):
    def generate(self, name: str, **options: object) -> object:
        return None


class TestRelativeOutputDirResolution:
    def test_relative_path_anchors_to_nearest_project(self, tmp_path: Path) -> None:
        project = tmp_path / "my-app"
        (project / "src").mkdir(parents=True)
        (project / "pyproject.toml").write_text(
            "[project]\nname = 'my-app'\nversion = '0.1.0'\n", encoding="utf-8"
        )
        gen = _StubGenerator(output_dir=project / "src" / "consumers")
        assert isinstance(gen.output_dir, Path)

    def test_absolute_output_dir_untouched(self, tmp_path: Path) -> None:
        gen = _StubGenerator(output_dir=tmp_path / "out")
        assert gen.output_dir == tmp_path / "out"

    def test_raw_output_dir_preserved_for_naming(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        project = tmp_path / "my-app"
        project.mkdir()
        (project / "pyproject.toml").write_text(
            "[project]\nname = 'my-app'\nversion = '0.1.0'\n", encoding="utf-8"
        )
        monkeypatch.chdir(project)

        gen = _StubGenerator(output_dir="src/consumers")
        assert gen.raw_output_dir == Path("src/consumers")
        assert gen.output_dir == project / "src" / "consumers"


class TestVirtualRootRefusal:
    def test_relative_path_at_virtual_root_raises_before_any_write(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        virtual_root = tmp_path / "workspace"
        virtual_root.mkdir()
        (virtual_root / "pyproject.toml").write_text(
            "[tool.uv.workspace]\nmembers = ['pkgs/*']\n", encoding="utf-8"
        )
        monkeypatch.chdir(virtual_root)
        target = virtual_root / "src" / "consumers"

        with pytest.raises(ValueError, match="absolute --output-dir"):
            _StubGenerator(output_dir="src/consumers")

        assert not target.exists(), "must not touch filesystem on refusal"

    def test_relative_path_without_any_project_raises(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        bare = tmp_path / "random-dir"
        bare.mkdir()
        monkeypatch.chdir(bare)

        with pytest.raises(ValueError, match="inside the package"):
            _StubGenerator(output_dir="src/gen")

    def test_relative_path_inside_member_anchors_to_member(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        workspace = tmp_path / "ws"
        member = workspace / "pkgs" / "lexigram-demo"
        member.mkdir(parents=True)
        (member / "sub" / "dir").mkdir(parents=True)
        (workspace / "pyproject.toml").write_text(
            "[tool.uv.workspace]\nmembers = ['pkgs/*']\n", encoding="utf-8"
        )
        (member / "pyproject.toml").write_text(
            "[project]\nname = 'lexigram-demo'\nversion = '0.1.0'\n",
            encoding="utf-8",
        )
        monkeypatch.chdir(member / "sub" / "dir")

        gen = _StubGenerator(output_dir="src/consumers")
        assert gen.output_dir == member / "src" / "consumers"


class TestNameContainment:
    """Path-traversal and content-injection guards (spec finding 15)."""

    def test_snake_case_rejects_path_separators(self) -> None:
        gen = _StubGenerator(output_dir="out")
        with pytest.raises(ValueError, match="Invalid generator name"):
            gen._validate_component_name("../../evil")

    def test_snake_case_rejects_absolute(self) -> None:
        gen = _StubGenerator(output_dir="out")
        with pytest.raises(ValueError, match="Invalid generator name"):
            gen._validate_component_name("/etc/passwd")

    def test_valid_names_pass(self) -> None:
        gen = _StubGenerator(output_dir="out")
        assert gen._validate_component_name("PetController") == "PetController"
        assert gen._validate_component_name("my-widget") == "my-widget"

    def test_write_file_rejects_escape(self, tmp_path: Path) -> None:
        out = tmp_path / "out"
        gen = _StubGenerator(output_dir=str(out))
        escape = out / ".." / "evil.py"
        with pytest.raises(ValueError, match="escapes output directory"):
            gen.write_file(escape, "x = 1\n")

    def test_write_file_allows_inside(self, tmp_path: Path) -> None:
        out = tmp_path / "out"
        gen = _StubGenerator(output_dir=str(out))
        result = gen.write_file(out / "ok.py", "x = 1\n")
        assert result.files_created == [out / "ok.py"]

    """Path-traversal and content-injection guards (spec finding 15)."""

    def test_snake_case_rejects_path_separators(self) -> None:
        gen = _StubGenerator(output_dir="out")
        with pytest.raises(ValueError, match="Invalid generator name"):
            gen._validate_component_name("../../evil")

    def test_snake_case_rejects_absolute(self) -> None:
        gen = _StubGenerator(output_dir="out")
        with pytest.raises(ValueError, match="Invalid generator name"):
            gen._validate_component_name("/etc/passwd")

    def test_valid_names_pass(self) -> None:
        gen = _StubGenerator(output_dir="out")
        assert gen._validate_component_name("PetController") == "PetController"
        assert gen._validate_component_name("my-widget") == "my-widget"

    def test_write_file_rejects_escape(self, tmp_path) -> None:
        out = tmp_path / "out"
        gen = _StubGenerator(output_dir=str(out))
        escape = out / ".." / "evil.py"
        with pytest.raises(ValueError, match="escapes output directory"):
            gen.write_file(escape, "x = 1\n")

    def test_write_file_allows_inside(self, tmp_path) -> None:
        out = tmp_path / "out"
        gen = _StubGenerator(output_dir=str(out))
        result = gen.write_file(out / "ok.py", "x = 1\n")
        assert result.files_created == [out / "ok.py"]

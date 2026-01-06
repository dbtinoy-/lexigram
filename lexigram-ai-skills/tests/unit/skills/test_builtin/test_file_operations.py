"""Tests for FileReadSkill and FileWriteSkill."""

from __future__ import annotations

import pytest

from lexigram.ai.skills.builtin.file_operations import FileReadSkill, FileWriteSkill
from lexigram.ai.skills.exceptions import SkillExecutionError


class TestFileReadSkill:
    """Tests for the file_read built-in skill."""

    @pytest.mark.asyncio
    async def test_read_existing_file(self, tmp_path) -> None:
        f = tmp_path / "test.txt"
        f.write_text("hello file")

        skill = FileReadSkill(base_dir=str(tmp_path))
        result = await skill.execute(path="test.txt")

        assert result.is_ok()
        output = result.unwrap().output
        assert output["content"] == "hello file"
        assert output["path"] == "test.txt"
        assert output["size_bytes"] == len("hello file".encode())

    @pytest.mark.asyncio
    async def test_read_missing_file_returns_err(self, tmp_path) -> None:
        skill = FileReadSkill(base_dir=str(tmp_path))
        result = await skill.execute(path="nonexistent.txt")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), SkillExecutionError)

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, tmp_path) -> None:
        skill = FileReadSkill(base_dir=str(tmp_path))
        result = await skill.execute(path="../../etc/passwd")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), SkillExecutionError)

    def test_definition_name(self, tmp_path) -> None:
        skill = FileReadSkill(base_dir=str(tmp_path))
        assert skill.definition.name == "file_read"

    def test_required_permission(self, tmp_path) -> None:
        skill = FileReadSkill(base_dir=str(tmp_path))
        assert "files.read" in skill.definition.permissions


class TestFileWriteSkill:
    """Tests for the file_write built-in skill."""

    @pytest.mark.asyncio
    async def test_write_creates_file(self, tmp_path) -> None:
        skill = FileWriteSkill(base_dir=str(tmp_path))
        result = await skill.execute(path="out.txt", content="data here")

        assert result.is_ok()
        written = (tmp_path / "out.txt").read_text()
        assert written == "data here"

    @pytest.mark.asyncio
    async def test_bytes_written_matches_content(self, tmp_path) -> None:
        content = "abcde"
        skill = FileWriteSkill(base_dir=str(tmp_path))
        result = await skill.execute(path="f.txt", content=content)
        assert result.unwrap().output["bytes_written"] == len(content.encode())

    @pytest.mark.asyncio
    async def test_path_traversal_blocked(self, tmp_path) -> None:
        skill = FileWriteSkill(base_dir=str(tmp_path))
        result = await skill.execute(path="../../evil.txt", content="bad")
        assert result.is_err()
        assert isinstance(result.unwrap_err(), SkillExecutionError)

    def test_definition_name(self, tmp_path) -> None:
        skill = FileWriteSkill(base_dir=str(tmp_path))
        assert skill.definition.name == "file_write"

    def test_required_permission(self, tmp_path) -> None:
        skill = FileWriteSkill(base_dir=str(tmp_path))
        assert "files.write" in skill.definition.permissions

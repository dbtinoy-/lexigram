from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from lexigram.cli.registry.version import (
    GitVersionSource,
    PyPackageVersionSource,
    VersionInfo,
    VersionRegistry,
    VersionSource,
    get_all_versions,
    get_version,
)


class TestVersionInfo:
    def test_creation(self) -> None:
        info = VersionInfo(name="pkg", version="1.0")
        assert info.name == "pkg"
        assert info.version == "1.0"
        assert info.installed is True


class TestVersionSource:
    def test_abc_cannot_be_instantiated(self) -> None:
        with pytest.raises(TypeError):
            VersionSource()


class TestPyPackageVersionSource:
    @patch("importlib.metadata.version", return_value="1.2.3")
    def test_get_version_found(self, mock_version: MagicMock) -> None:
        source = PyPackageVersionSource("lexigram")
        assert source.get_version() == "1.2.3"

    @patch("importlib.metadata.version", side_effect=RuntimeError)
    def test_get_version_error(self, mock_version: MagicMock) -> None:
        source = PyPackageVersionSource("nonexistent")
        assert source.get_version() is None


class TestGitVersionSource:
    @patch("lexigram.cli.registry.version.subprocess.run")
    def test_get_version_success(self, mock_run: MagicMock) -> None:
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout.strip.return_value = "v1.0.0"
        mock_run.return_value = mock_result
        source = GitVersionSource()
        assert source.get_version() is not None

    @patch("lexigram.cli.registry.version.subprocess.run", side_effect=RuntimeError)
    def test_get_version_error(self, mock_run: MagicMock) -> None:
        source = GitVersionSource()
        assert source.get_version() is None


class TestVersionRegistry:
    def test_register_and_get(self) -> None:
        VersionRegistry._sources = {}
        VersionRegistry._initialized = False
        source = MagicMock(spec=VersionSource)
        VersionRegistry.register("test", source)
        assert VersionRegistry.get("test") is source

    def test_get_nonexistent(self) -> None:
        VersionRegistry._sources = {}
        VersionRegistry._initialized = False
        assert VersionRegistry.get("nonexistent") is None

    def test_get_all(self) -> None:
        VersionRegistry._sources = {}
        VersionRegistry._initialized = False
        source = MagicMock(spec=VersionSource)
        VersionRegistry.register("a", source)
        all_sources = VersionRegistry.get_all()
        assert "a" in all_sources

    def test_register_defaults(self) -> None:
        VersionRegistry._sources = {}
        VersionRegistry._initialized = False
        VersionRegistry.register_defaults()
        assert VersionRegistry._initialized is True
        assert VersionRegistry.get("lexigram") is not None
        assert VersionRegistry.get("python") is not None


class TestGetVersion:
    @patch("lexigram.cli.registry.version.PyPackageVersionSource.get_version", return_value="1.0")
    def test_get_version_registered(self, mock_get: MagicMock) -> None:
        VersionRegistry._sources = {"test": MagicMock()}
        VersionRegistry._sources["test"].get_version.return_value = "2.0"
        VersionRegistry._initialized = True
        result = get_version("test")
        assert result == "2.0"

    @patch("lexigram.cli.registry.version.PyPackageVersionSource.get_version", return_value="3.0")
    def test_get_version_unregistered(self, mock_get: MagicMock) -> None:
        VersionRegistry._sources = {}
        VersionRegistry._initialized = False
        with patch.object(VersionRegistry, "get", return_value=None):
            result = get_version("unknown_pkg")
            assert result is not None


class TestGetAllVersions:
    def test_returns_dict(self) -> None:
        VersionRegistry._sources = {}
        VersionRegistry._initialized = True
        source = MagicMock(spec=VersionSource)
        source.get_version.return_value = "1.0"
        VersionRegistry.register("pkg", source)
        versions = get_all_versions()
        assert "pkg" in versions
        assert versions["pkg"] == "1.0"

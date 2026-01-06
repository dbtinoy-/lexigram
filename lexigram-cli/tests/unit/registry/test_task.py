from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from lexigram.cli.registry.task import (
    MypyRunner,
    PytestRunner,
    RuffRunner,
    TaskResult,
    TaskRunner,
    TaskRunnerRegistry,
)


class TestTaskResult:
    def test_defaults(self) -> None:
        r = TaskResult(success=True)
        assert r.success is True
        assert r.message == ""
        assert r.exit_code == 0

    def test_failure(self) -> None:
        r = TaskResult(success=False, message="fail", exit_code=1)
        assert r.success is False
        assert r.exit_code == 1


class TestTaskRunner:
    def test_abc_cannot_be_instantiated(self) -> None:
        with pytest.raises(TypeError):
            TaskRunner()


class TestPytestRunner:
    def test_is_available_true(self) -> None:
        with patch("lexigram.cli.registry.task.shutil.which", return_value="/usr/bin/pytest"):
            runner = PytestRunner()
            assert runner.is_available() is True

    def test_is_available_false(self) -> None:
        with patch("lexigram.cli.registry.task.shutil.which", return_value=None):
            runner = PytestRunner()
            assert runner.is_available() is False

    def test_run_success(self) -> None:
        with patch("lexigram.cli.registry.task.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = "tests passed"
            mock_run.return_value = mock_result

            runner = PytestRunner()
            result = runner.run()
            assert result.success is True
            assert result.exit_code == 0

    def test_run_failure(self) -> None:
        with patch("lexigram.cli.registry.task.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 1
            mock_result.stdout = ""
            mock_result.stderr = "fail"
            mock_run.return_value = mock_result

            runner = PytestRunner()
            result = runner.run()
            assert result.success is False
            assert result.exit_code == 1

    def test_run_with_options(self) -> None:
        with patch("lexigram.cli.registry.task.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_result.stdout = ""
            mock_run.return_value = mock_result

            runner = PytestRunner()
            result = runner.run(path="tests/", coverage=True, verbose=True)
            assert result.success is True

    def test_run_subprocess_error(self) -> None:
        with patch("lexigram.cli.registry.task.subprocess.run", side_effect=OSError("no pytest")):
            runner = PytestRunner()
            result = runner.run()
            assert result.success is False

    def test_name(self) -> None:
        assert PytestRunner().get_name() == "pytest"


class TestRuffRunner:
    def test_is_available_true(self) -> None:
        with patch("lexigram.cli.registry.task.shutil.which", return_value="/usr/bin/ruff"):
            runner = RuffRunner()
            assert runner.is_available() is True

    def test_run_success(self) -> None:
        with patch("lexigram.cli.registry.task.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            runner = RuffRunner()
            result = runner.run()
            assert result.success is True

    def test_run_with_fix(self) -> None:
        with patch("lexigram.cli.registry.task.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            runner = RuffRunner()
            result = runner.run(fix=True)
            assert result.success is True

    def test_run_subprocess_error(self) -> None:
        with patch("lexigram.cli.registry.task.subprocess.run", side_effect=OSError):
            runner = RuffRunner()
            result = runner.run()
            assert result.success is False

    def test_name(self) -> None:
        assert RuffRunner().get_name() == "ruff"


class TestMypyRunner:
    def test_is_available_true(self) -> None:
        with patch("lexigram.cli.registry.task.shutil.which", return_value="/usr/bin/mypy"):
            runner = MypyRunner()
            assert runner.is_available() is True

    def test_run_success(self) -> None:
        with patch("lexigram.cli.registry.task.subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            runner = MypyRunner()
            result = runner.run()
            assert result.success is True

    def test_run_subprocess_error(self) -> None:
        with patch("lexigram.cli.registry.task.subprocess.run", side_effect=OSError):
            runner = MypyRunner()
            result = runner.run()
            assert result.success is False

    def test_name(self) -> None:
        assert MypyRunner().get_name() == "mypy"


class TestTaskRunnerRegistry:
    def test_register_and_get(self) -> None:
        TaskRunnerRegistry._runners = {}
        TaskRunnerRegistry._initialized = False
        TaskRunnerRegistry.register(PytestRunner)
        runner = TaskRunnerRegistry.get("pytest")
        assert runner is not None
        assert runner.name == "pytest"

    def test_get_nonexistent(self) -> None:
        TaskRunnerRegistry._runners = {}
        TaskRunnerRegistry._initialized = False
        assert TaskRunnerRegistry.get("nonexistent") is None

    def test_get_all(self) -> None:
        TaskRunnerRegistry._runners = {}
        TaskRunnerRegistry._initialized = False
        TaskRunnerRegistry.register(PytestRunner)
        all_runners = TaskRunnerRegistry.get_all()
        assert "pytest" in all_runners

    def test_get_available(self) -> None:
        TaskRunnerRegistry._runners = {}
        TaskRunnerRegistry._initialized = False
        def which_side_effect(cmd: str) -> str | None:
            mapping = {"pytest": "/usr/bin/pytest", "ruff": None, "mypy": "/usr/bin/mypy"}
            return mapping.get(cmd)
        with patch("lexigram.cli.registry.task.shutil.which", side_effect=which_side_effect):
            TaskRunnerRegistry.register_defaults()
            available = TaskRunnerRegistry.get_available()
            assert len(available) == 2
            names = [r.name for r in available]
            assert "pytest" in names
            assert "mypy" in names
            assert "ruff" not in names

    def test_register_defaults(self) -> None:
        TaskRunnerRegistry._runners = {}
        TaskRunnerRegistry._initialized = False
        TaskRunnerRegistry.register_defaults()
        assert TaskRunnerRegistry._initialized is True
        assert TaskRunnerRegistry.get("pytest") is not None
        assert TaskRunnerRegistry.get("ruff") is not None

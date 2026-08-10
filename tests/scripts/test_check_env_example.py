from __future__ import annotations

from pathlib import Path

from scripts.check_env_example import main


def _write_example(path: Path, names: list[str]) -> None:
    lines = ["LEX_DEBUG=false  # debug toggle"] + [f"{name}=" for name in names]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _run_check(root: Path, example: Path) -> int:
    import sys

    old_argv = sys.argv
    sys.argv = ["check_env_example.py", "--root", str(root), "--example", str(example)]
    try:
        return main()
    finally:
        sys.argv = old_argv


def test_check_passes_when_all_references_documented(tmp_path: Path) -> None:
    example = tmp_path / ".env.example"
    _write_example(example, ["DATABASE_URL", "LEX_PROFILE"])
    source = tmp_path / "lexigram" / "src"
    source.mkdir(parents=True)
    (source / "doctor.py").write_text(
        'import os\nurl = os.getenv("DATABASE_URL")\n',
        encoding="utf-8",
    )

    assert _run_check(tmp_path, example) == 0


def test_check_fails_when_reference_missing_from_example(tmp_path: Path) -> None:
    example = tmp_path / ".env.example"
    _write_example(example, [])
    source = tmp_path / "lexigram" / "src"
    source.mkdir(parents=True)
    (source / "doctor.py").write_text(
        'import os\nurl = os.environ.get("DATABASE_URL")\n',
        encoding="utf-8",
    )

    assert _run_check(tmp_path, example) == 1


def test_check_reports_each_missing_variable(tmp_path: Path, capsys: object) -> None:
    example = tmp_path / ".env.example"
    _write_example(example, [])
    source = tmp_path / "lexigram" / "src"
    source.mkdir(parents=True)
    (source / "doctor.py").write_text(
        'import os\na = os.environ["JWT_SECRET"]\nb = os.getenv("BROKER_URL")\n',
        encoding="utf-8",
    )

    assert _run_check(tmp_path, example) == 1
    captured = capsys.readouterr()  # type: ignore[attr-defined]
    assert "JWT_SECRET" in captured.out
    assert "BROKER_URL" in captured.out


def test_check_finds_dynamic_same_line_references(tmp_path: Path) -> None:
    example = tmp_path / ".env.example"
    _write_example(example, [])
    source = tmp_path / "lexigram-ai" / "src"
    source.mkdir(parents=True)
    (source / "doctor.py").write_text(
        "import os\n"
        'keys = [key for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY") '
        "if os.environ.get(key)]\n",
        encoding="utf-8",
    )

    assert _run_check(tmp_path, example) == 1
    assert _run_check(tmp_path, example) == 1  # stable across runs


def test_check_ignores_test_dirs_and_vcs(tmp_path: Path) -> None:
    example = tmp_path / ".env.example"
    _write_example(example, [])
    tests_dir = tmp_path / "lexigram" / "tests"
    tests_dir.mkdir(parents=True)
    (tests_dir / "test_doctor.py").write_text(
        'import os\nx = os.environ.get("TEST_ONLY_VAR")\n',
        encoding="utf-8",
    )
    vcs_dir = tmp_path / ".venv"
    vcs_dir.mkdir()
    (vcs_dir / "site.py").write_text(
        'import os\nx = os.environ.get("VENV_ONLY_VAR")\n',
        encoding="utf-8",
    )

    assert _run_check(tmp_path, example) == 0


def test_check_fails_when_example_missing(tmp_path: Path) -> None:
    example = tmp_path / ".env.example"
    source = tmp_path / "lexigram" / "src"
    source.mkdir(parents=True)

    assert _run_check(tmp_path, example) == 1


def test_check_matches_full_repo_example() -> None:
    import scripts.check_env_example as check

    assert _run_check(check.ROOT, check.ROOT / ".env.example") == 0

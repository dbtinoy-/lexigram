from __future__ import annotations

from pathlib import Path

from dev.checks.env_binding import documented_vars, run_check


def _write_example(path: Path, names: list[str]) -> None:
    lines = ["# generated"] + [f"{name}=placeholder" for name in names]
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def test_documented_vars_parses_names_and_dedupes(tmp_path: Path) -> None:
    example = tmp_path / ".env.example"
    example.write_text(
        "LEX_WEB__HOST=0.0.0.0\n"
        "# comment\n"
        "DATABASE_URL=postgres://x\n"
        "LEX_WEB__HOST=0.0.0.0\n",
        encoding="utf-8",
    )

    assert documented_vars(example) == ["LEX_WEB__HOST", "DATABASE_URL"]


def test_run_check_fails_on_dead_variable() -> None:
    verdicts = {"LEX_WEB__HOST": False, "LEX_CACHE__BACKEND": True}

    code = run_check(list(verdicts), probe=verdicts.get)

    assert code == 1


def test_run_check_passes_when_all_live_or_unknown() -> None:
    verdicts = {"LEX_WEB__HOST": True, "LEX_MYSTERY__X": None}

    code = run_check(list(verdicts), probe=verdicts.get)

    assert code == 0


def test_run_check_strict_fails_on_unknown() -> None:
    verdicts = {"LEX_WEB__HOST": True, "LEX_MYSTERY__X": None}

    code = run_check(list(verdicts), strict=True, probe=verdicts.get)

    assert code == 1


def test_run_check_skips_non_lex_variables() -> None:
    calls: list[str] = []

    def probe(name: str) -> bool | None:
        calls.append(name)
        return True

    code = run_check(["DATABASE_URL", "LEX_WEB__HOST"], probe=probe)

    assert code == 0
    assert calls == ["LEX_WEB__HOST"]


def test_full_repo_example_probes_live() -> None:
    import dev.checks.env_binding as check

    names = [n for n in documented_vars(check.EXAMPLE) if n.startswith("LEX_")]
    assert names, "expected LEX_ variables in the repo .env.example"
    # Spot-check a small deterministic sample rather than probing all ~1000
    # (each probe runs real from_yaml loads; full sweep belongs in CI).
    sample = sorted(names)[-5:]

    assert run_check(sample, strict=False) == 0


def test_full_sweep_finds_no_dead_vars() -> None:
    import dev.checks.env_binding as check

    names = [n for n in documented_vars(check.EXAMPLE) if n.startswith("LEX_")]

    # Full empirical sweep: every LEX_ var must bind through its family's
    # real from_yaml path (or be an uncovered family). Slow (~2 min) but
    # this is the accuracy guarantee for the whole documentation pipeline.
    assert run_check(names, strict=False) == 0

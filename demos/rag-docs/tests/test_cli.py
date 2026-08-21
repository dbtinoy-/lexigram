"""Tests for the docs-ask CLI commands."""

from __future__ import annotations

import contextlib
import io
from pathlib import Path

from rag_docs.main import _build_parser, _run, resolve_default_docs_dir


def make_corpus(root: Path) -> Path:
    docs = root / "docs"
    docs.mkdir(parents=True)
    (docs / "modules.md").write_text(
        "# Modules\n\nModules export services through the exports list.\n"
        "Providers register services during application boot.\n"
    )
    return docs


async def test_ask_captures_output(tmp_path: Path) -> None:
    docs = make_corpus(tmp_path)
    buffer = io.StringIO()
    args = _build_parser().parse_args(
        ["ask", "how do modules export services?", "--docs-dir", str(docs)]
    )

    with contextlib.redirect_stdout(buffer):
        code = await _run(args)

    out = buffer.getvalue()
    assert code == 0
    assert "[1] modules.md#" in out
    assert "error:" not in out


async def test_unknown_strategy_prints_error_and_exits_nonzero(
    tmp_path: Path,
) -> None:
    docs = make_corpus(tmp_path)
    buffer = io.StringIO()
    args = _build_parser().parse_args(
        ["ask", "anything", "--strategy", "bm25", "--docs-dir", str(docs)]
    )

    with contextlib.redirect_stdout(buffer):
        code = await _run(args)

    out = buffer.getvalue()
    assert code == 1
    assert "error:" in out


async def test_demo_runs_canned_questions(tmp_path: Path) -> None:
    docs = make_corpus(tmp_path)
    buffer = io.StringIO()
    args = _build_parser().parse_args(["demo", "--docs-dir", str(docs)])

    with contextlib.redirect_stdout(buffer):
        code = await _run(args)

    out = buffer.getvalue()
    assert code == 0
    assert "Q:" in out
    assert "[1]" in out


async def test_index_prints_stats(tmp_path: Path) -> None:
    docs = make_corpus(tmp_path)
    buffer = io.StringIO()
    args = _build_parser().parse_args(["index", "--docs-dir", str(docs)])

    with contextlib.redirect_stdout(buffer):
        code = await _run(args)

    out = buffer.getvalue()
    assert code == 0
    assert "indexed 1 files /" in out


async def test_default_docs_dir_points_at_repo_docs() -> None:
    default_dir = resolve_default_docs_dir()

    assert default_dir.name == "docs"
    assert default_dir.exists()

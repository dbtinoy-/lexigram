"""CLI routing and smoke tests (in-process)."""

from __future__ import annotations

import pytest

from feedback_loop.main import build_parser, run


class TestParser:
    def test_routes(self) -> None:
        p = build_parser()
        assert p.parse_args(["ask", "track-order", "--owner", "a"]).command == "ask"
        rate = p.parse_args(
            ["rate", "t3", "2", "--owner", "a", "--comment", "bad"],
        )
        assert rate.command == "rate" and rate.rating == 2.0
        assert p.parse_args(["stats", "--owner", "a"]).command == "stats"
        assert p.parse_args(["regress", "--owner", "a"]).command == "regress"
        assert p.parse_args(["report", "rid"]).command == "report"
        assert p.parse_args(["demo"]).command == "demo"

    def test_requires_command(self) -> None:
        with pytest.raises(SystemExit):
            build_parser().parse_args([])


class TestRun:
    @pytest.mark.asyncio
    async def test_demo_full_loop(self, capsys, tmp_path) -> None:
        args = build_parser().parse_args(
            ["demo", "--experiment-dir", str(tmp_path)],
        )
        code = await run(args)
        out = capsys.readouterr().out

        assert code == 0
        failing_line = out.split("failing:")[1]
        assert "t1" in failing_line and "t2" in failing_line
        assert "t3" not in failing_line and "t4" not in failing_line

    @pytest.mark.asyncio
    async def test_typed_error_exits_one(self, capsys, tmp_path) -> None:
        args = build_parser().parse_args(
            ["ask", "nope", "--owner", "a",
             "--experiment-dir", str(tmp_path)],
        )
        code = await run(args)

        assert code == 1
        assert "unknown question" in capsys.readouterr().out.lower()

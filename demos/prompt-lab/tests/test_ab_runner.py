"""Deterministic A/B scoring tests."""

from __future__ import annotations

import pytest

from prompt_lab.services.ab_runner import ABRunner
from prompt_lab.repository.responders import RESPONDERS
from prompt_lab.repository.templates import TEMPLATES
from prompt_lab.services.versioning import LabVersions


@pytest.fixture
def runner() -> ABRunner:
    versions = LabVersions(max_versions=10)
    versions.seed(TEMPLATES)
    return ABRunner(versions=versions)


class TestResponders:
    def test_v1_clipped_style(self) -> None:
        out = RESPONDERS.get("v1")("Where is my order?")
        assert out.startswith("Order issue noted.")
        assert "happy to help" not in out

    def test_v2_warm_style(self) -> None:
        out = RESPONDERS.get("v2")("Where is my order?")
        assert "happy to help" in out


class TestABRunner:
    async def test_scores_are_deterministic(self, runner) -> None:
        first = await runner.run_all()
        second = await runner.run_all()

        assert first == second

    async def test_v2_outscores_v1(self, runner) -> None:
        report = await runner.run_all()
        scores = {k: v["average_score"] for k, v in report["variants"].items()}

        assert scores["v2"] > scores["v1"]

    async def test_winner_is_v2(self, runner) -> None:
        report = await runner.run_all()

        assert report["winner"] == "v2"

    async def test_totals_cover_all_cases(self, runner) -> None:
        report = await runner.run_all()

        assert all(v["total"] == 4 for v in report["variants"].values())

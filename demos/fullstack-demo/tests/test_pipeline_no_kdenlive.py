"""Phase 4: the kdenlive path is removed - the pipeline is a pure ffmpeg
flow with no kdenlive_api dependency and no renderer switch.
"""

from pathlib import Path
from unittest.mock import AsyncMock

import pytest
import yaml

import shorts_creator.pipeline.pipeline as pipeline_mod
from shorts_creator.pipeline.pipeline import ReelPipeline

APP_ROOT = Path(__file__).parents[1]


def test_pipeline_source_has_no_kdenlive_api_dependency() -> None:
    src = Path(pipeline_mod.__file__).read_text()
    assert "kdenlive_api" not in src
    assert "kdenlive" not in src.lower()
    assert "RENDERER" not in src


@pytest.mark.asyncio
async def test_run_dispatches_ffmpeg_flow() -> None:
    pipeline = ReelPipeline()
    pipeline._run_ffmpeg = AsyncMock(return_value=True)

    ok = await pipeline.run()

    assert ok is True
    pipeline._run_ffmpeg.assert_awaited_once()


@pytest.mark.asyncio
async def test_run_propagates_ffmpeg_failure() -> None:
    pipeline = ReelPipeline()
    pipeline._run_ffmpeg = AsyncMock(return_value=False)

    ok = await pipeline.run()

    assert ok is False
    pipeline._run_ffmpeg.assert_awaited_once()


def test_application_yaml_has_no_renderer_switch() -> None:
    raw = (APP_ROOT / "application.yaml").read_text()
    assert "kdenlive" not in raw.lower()
    data = yaml.safe_load(raw)
    assert "renderer" not in data.get("pipeline", {})

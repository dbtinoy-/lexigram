"""Health-check generator regression tests."""

from __future__ import annotations

import ast
from pathlib import Path

import pytest

from lexigram.sql.cli.generators.health_check import HealthCheckGenerator


@pytest.mark.asyncio
async def test_generated_health_check_returns_canonical_result(tmp_path: Path) -> None:
    """Generated checks must use HealthCheckResult's component/error fields."""
    result = HealthCheckGenerator(tmp_path).generate("DiskSpace")
    path = Path(result.files_created[0])
    content = path.read_text()
    ast.parse(content)

    namespace: dict[str, object] = {}
    exec(compile(content, str(path), "exec"), namespace)  # noqa: S102
    check = namespace["DiskSpace"]()
    health = await check.check()  # type: ignore[union-attr]

    assert health.component == "disk_space"
    assert health.status.value == "healthy"
    assert health.details == {}

"""Behavioral test for the live phone preview: loads the real
composer-preview.js with a stubbed DOM, drives changes through the actual
bound widget listeners, and asserts the preview output updates accordingly.

Requires node on PATH; skipped when unavailable.
"""

import shutil
import subprocess
from pathlib import Path

import pytest

HARNESS = Path(__file__).parent / "js" / "preview_fields_test.js"
EXPECTED = "85 passed, 0 failed"


@pytest.mark.skipif(shutil.which("node") is None, reason="node not available")
def test_preview_consumes_form_fields():
    result = subprocess.run(
        ["node", str(HARNESS)],
        capture_output=True,
        text=True,
        timeout=60,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert EXPECTED in result.stdout, result.stdout

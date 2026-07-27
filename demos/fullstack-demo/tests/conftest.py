"""Load the project .env into os.environ once, before any app import.

Several tests render the real application.yaml (e.g. the global settings
pages, app config, migration boot checks), which interpolates values like
${OPENCODE_ZEN_API_KEY} from the environment. Sourcing .env here keeps the
suite runnable without a manual `set -a && source .env` before pytest.
"""

import os
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[1]


def _load_dotenv(path: Path) -> None:
    if not path.exists():
        return
    for raw in path.read_text().splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in ("'", '"'):
            value = value[1:-1]
        if key and key not in os.environ:
            os.environ[key] = value


_load_dotenv(_REPO_ROOT / ".env")

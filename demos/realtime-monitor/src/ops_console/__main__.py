"""Module entry point: ``python -m ops_console``."""

from __future__ import annotations

import sys

from ops_console.main import main

if __name__ == "__main__":
    sys.exit(main())

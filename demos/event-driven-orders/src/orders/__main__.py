"""Module entry point: ``python -m orders``."""

from __future__ import annotations

import sys

from orders.main import main

if __name__ == "__main__":
    sys.exit(main())

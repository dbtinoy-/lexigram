"""Module entry point.

``python -m orders`` → boot the app and serve the order console.
"""

from __future__ import annotations

import sys

from orders.main import main

if __name__ == "__main__":
    sys.exit(main())

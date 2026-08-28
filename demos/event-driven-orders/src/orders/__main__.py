"""Module entry point.

``python -m orders`` boots the app and serves the order console;
``python -m orders demo`` runs the full lifecycle and exits.
"""

from __future__ import annotations

import sys

from orders.main import main

if __name__ == "__main__":
    sys.exit(main())

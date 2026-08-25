"""Module entry point.

``python -m orders``                 → serve the REST API
``python -m orders <command> [...]`` → teaching CLI (place/pay/ship/…)
"""

from __future__ import annotations

import sys


def main() -> None:
    from orders.cli import main as cli_main
    from orders.main import main as serve_main

    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        sys.exit(serve_main())
    sys.exit(cli_main(sys.argv[1:]))


main()

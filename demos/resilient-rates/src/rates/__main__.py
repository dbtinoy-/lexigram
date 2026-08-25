"""Module entry point.

``python -m rates``            → serve the REST API
``python -m rates <command>``  → teaching CLI (fetch/scenario/stats/…)
"""

from __future__ import annotations

import sys


def main() -> None:
    from rates.cli import main as cli_main
    from rates.main import main as serve_main

    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        serve_main()
        return
    sys.exit(cli_main(sys.argv[1:]))


if __name__ == "__main__":
    main()

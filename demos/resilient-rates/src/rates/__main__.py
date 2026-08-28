"""Module entry point.

``python -m rates`` serves the rate desk UI; ``python -m rates demo`` runs
an offline five-act walkthrough and exits.
"""

from __future__ import annotations


def main() -> None:
    from rates.main import main as serve_main

    serve_main()


if __name__ == "__main__":
    main()

"""Module entry point.

``python -m rates`` boots the REST API and serves the rate desk UI.
"""

from __future__ import annotations


def main() -> None:
    from rates.main import main as serve_main

    serve_main()


if __name__ == "__main__":
    main()

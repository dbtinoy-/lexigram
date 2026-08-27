"""Module entry point.

``python -m webhookrelay`` boots the REST API and serves the webhook relay.
"""

from __future__ import annotations


def main() -> None:
    from webhookrelay.main import main as serve_main

    serve_main()


if __name__ == "__main__":
    main()

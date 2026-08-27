"""Module entry point.

``python -m queueworker`` boots the REST API and serves the queue worker.
"""

from __future__ import annotations


def main() -> None:
    from queueworker.main import main as serve_main

    serve_main()


if __name__ == "__main__":
    main()

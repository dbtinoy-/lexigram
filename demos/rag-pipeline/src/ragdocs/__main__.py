"""Module entry point.

``python -m ragdocs`` boots the REST API and serves the RAG pipeline.
"""

from __future__ import annotations


def main() -> None:
    from ragdocs.main import main as serve_main

    serve_main()


if __name__ == "__main__":
    main()

"""Module entry point.

``python -m content_gen`` boots the REST API and serves the content generator.
"""

from __future__ import annotations


def main() -> None:
    from content_gen.main import main as serve_main

    serve_main()


if __name__ == "__main__":
    main()

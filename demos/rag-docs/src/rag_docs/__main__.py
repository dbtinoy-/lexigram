"""Module entry point.

``python -m rag_docs``                 → serve the REST API
``python -m rag_docs <command> [...]`` → teaching CLI (index/ask/demo)
"""

from __future__ import annotations

import sys


def main() -> None:
    from rag_docs.cli import main as cli_main
    from rag_docs.main import main as serve_main

    if len(sys.argv) > 1 and sys.argv[1] == "serve":
        sys.exit(serve_main())
    sys.exit(cli_main(sys.argv[1:]))


main()

"""Module entry point.

``python -m rag_docs`` → boot the app and serve the split-screen console.
"""

from __future__ import annotations

import sys

from rag_docs.main import main

if __name__ == "__main__":
    sys.exit(main())

"""Module entry point.

``python -m rag_docs`` boots the app and serves the split-screen console;
``python -m rag_docs demo`` runs three cited questions and exits.
"""

from __future__ import annotations

import sys

from rag_docs.main import main

if __name__ == "__main__":
    sys.exit(main())

"""Module entry point: default to the server; forward CLI args when given."""

from __future__ import annotations

import sys

from rates.cli import main as cli_main
from rates.main import main as serve_main

if len(sys.argv) > 1:
    sys.exit(cli_main(sys.argv[1:]))
serve_main()

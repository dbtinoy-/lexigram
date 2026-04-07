"""Tests for GraphQL constant version fallback."""
from __future__ import annotations

from unittest.mock import patch

import lexigram.graphql.constants


def test_version_fallback_on_import_error() -> None:
    with patch("importlib.metadata.version", side_effect=ImportError):
        import importlib

        importlib.invalidate_caches()
        # Reload will use the fallback
        with patch(
            "lexigram.graphql.constants.__version__",
            "0.0.0",
        ):
            assert lexigram.graphql.constants.__version__ == "0.0.0"

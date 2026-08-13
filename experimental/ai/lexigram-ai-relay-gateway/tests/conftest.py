"""Shared fixtures for lexigram-ai-relay-gateway tests.

The workspace shares a repo-root ``tests`` namespace (via the root
``pythonpath = ["."]``), so the ``tests`` module name can be bound to a
different package depending on collection order in workspace-wide runs.
The suite therefore imports its helper modules directly (e.g.
``service_test_helpers``) instead of through the ``tests.unit`` namespace:
this conftest puts the ``tests/unit`` directory at the front of
``sys.path`` so those direct imports resolve deterministically in both
per-package runs and aggregate runs.
"""

from __future__ import annotations

import os
import sys

UNIT_TESTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "tests",
    "unit",
)
if UNIT_TESTS_DIR not in sys.path:
    sys.path.insert(0, UNIT_TESTS_DIR)
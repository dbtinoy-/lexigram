"""Path shim for unit test support imports.

pytest's ``--import-mode=importlib`` does not put test directories on
``sys.path`` and this directory has no ``__init__.py``, so bare-name
imports of sibling support modules (e.g. ``channel_registry_support``)
resolve through this fronted path in both per-package runs and
aggregate runs from the monorepo root.
"""

from __future__ import annotations

import os
import sys

_UNIT_DIR = os.path.dirname(os.path.abspath(__file__))
if _UNIT_DIR not in sys.path:
    sys.path.insert(0, _UNIT_DIR)

"""Env-var catalog generator package.

Generates ``REF_ENV_VARS.md`` by scanning config classes across the
workspace. Run as a module: ``python -m dev.catalogs.env_vars_catalog``.
Implementation: :mod:`_model`, :mod:`scan`, :mod:`env_paths`,
:mod:`main`.
"""

from __future__ import annotations

from dev.catalogs.env_vars_catalog.main import main

__all__ = ["main"]

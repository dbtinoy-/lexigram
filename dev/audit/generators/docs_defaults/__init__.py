"""Docs defaults audit generator package.

Public API: :class:`DocsDefaultsAuditGenerator`. Implementation is split
across :mod:`universe` (real config-default index), :mod:`claims`
(claim parsing/comparison), and :mod:`generator` (audit driver).
"""

from __future__ import annotations

from dev.audit.generators.docs_defaults.generator import DocsDefaultsAuditGenerator

__all__ = ["DocsDefaultsAuditGenerator"]

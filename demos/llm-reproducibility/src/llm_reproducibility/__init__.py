"""Seeded, reproducible LLM relay experiment package.

Same seed + same ``config.yaml`` => byte-identical metrics, params,
and conversion results. Implementation: :mod:`metrics` (JSON sink),
:mod:`results` (result model, digests, deltas), :mod:`runner`
(execution + persistence).
"""

from __future__ import annotations

from llm_reproducibility.module import ExperimentModule

__all__ = ["ExperimentModule"]

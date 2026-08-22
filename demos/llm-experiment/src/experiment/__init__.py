"""Seeded, reproducible LLM relay experiment package.

Same seed + same ``experiment.yaml`` => byte-identical metrics, params,
and conversion results. Implementation: :mod:`metrics` (JSON sink),
:mod:`results` (result model, digests, deltas), :mod:`runner`
(execution + persistence).
"""

from __future__ import annotations

from experiment.module import ExperimentModule

__all__ = ["ExperimentModule"]

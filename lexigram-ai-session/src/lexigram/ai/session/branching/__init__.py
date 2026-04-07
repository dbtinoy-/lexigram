"""Branching subpackage — fork and merge session timelines."""

from __future__ import annotations

from lexigram.ai.session.branching.branch_manager import BranchManager
from lexigram.ai.session.branching.merge import (
    AppendMerge,
    MergeStrategy,
    SelectiveMerge,
)

__all__ = [
    "AppendMerge",
    "BranchManager",
    "MergeStrategy",
    "SelectiveMerge",
]

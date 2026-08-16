"""Result type — backward-compatible re-export.

Canonical location: lexigram.contracts.core.result
"""

from __future__ import annotations

from lexigram.contracts.core.result import Err as Err
from lexigram.contracts.core.result import Ok as Ok
from lexigram.contracts.core.result import Result as Result
from lexigram.contracts.core.result import UnwrapError as UnwrapError

__all__ = ["Err", "Ok", "Result"]

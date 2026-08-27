"""DI wiring for the feedback-loop demo (internal).

Convention: providers register contracts-to-implementations mappings in
``register()`` and resolve collaborators in ``boot()``.  This keeps the
dependency graph explicit and testable.
"""

from __future__ import annotations

from feedback_loop.di.provider import LoopProvider

__all__ = ["LoopProvider"]

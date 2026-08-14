"""Models module for lexigram-admin.

Re-exports AdminUser and related models.
"""

from __future__ import annotations

from lexigram.admin.auth.integration import AdminUser

__all__ = ["AdminUser"]

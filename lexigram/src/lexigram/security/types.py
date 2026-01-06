"""Type definitions for lexigram core security."""

from __future__ import annotations

from lexigram.contracts.security.rotation import (
    SecretRotationPolicy as SecretRotationPolicy,  # re-export
)

__all__ = ["SecretRotationPolicy"]

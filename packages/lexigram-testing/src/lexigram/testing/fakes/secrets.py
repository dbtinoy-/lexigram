"""In-memory rotatable secret store — provided as a test fake.

The implementation is the production ``memory`` backend owned by
``lexigram.secrets``; this module re-exports it so test code can keep
importing the fake from ``lexigram.testing``.
"""

from __future__ import annotations

from lexigram.secrets.backends.memory import InMemoryRotatableSecretStore

__all__ = ["FakeRotatableSecretStore"]

FakeRotatableSecretStore = InMemoryRotatableSecretStore

"""JSON API controllers for the resilient rates demo.

Convention followed: **Controller pattern** — each handler resolves its
dependencies from the container and returns domain ``Result`` values.

Exports:

- ``RatesApiController`` — REST endpoints for the rate desk
"""

from __future__ import annotations

from rates.controllers.api import RatesApiController

__all__ = ["RatesApiController"]

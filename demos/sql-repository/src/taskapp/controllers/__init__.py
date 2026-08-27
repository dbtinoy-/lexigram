"""HTTP controllers — expose services over HTTP.

Controllers are thin adapters between HTTP requests and services.
They validate input, call services, and format responses.
"""

from __future__ import annotations

from taskapp.controllers.api import TasksApiController

__all__ = ["TasksApiController"]

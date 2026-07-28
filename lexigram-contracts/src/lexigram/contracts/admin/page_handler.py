"""Management page handler protocols for lexigram-admin contributors.

``handle_action`` is duck-typed (not part of the protocol) so that
handlers with only ``handle`` satisfy ``isinstance(handler, ManagementPageHandler)``.
The framework uses ``hasattr(handler, "handle_action")`` to discover action support.
"""

from __future__ import annotations

from typing import Any, Protocol, runtime_checkable


@runtime_checkable
class ManagementPageHandler(Protocol):
    """Protocol for contributor management page handlers.

    Implement this instead of registering dotted-string handler paths
    in ``ManagementPageDefinition``.  The framework discovers handlers
    that satisfy this protocol and dispatches requests directly.

    To support POST actions, define an additional ``handle_action(request, action_name)``
    method.  It is checked at runtime via ``hasattr``, not structurally typed here.
    """

    async def handle(self, request: Any) -> Any:
        """Handle a GET request for the management page."""
        ...


# Backward-compatible alias — existing code importing AdminPageHandlerProtocol
# continues to work without changes.
AdminPageHandlerProtocol = ManagementPageHandler

__all__ = ["AdminPageHandlerProtocol", "ManagementPageHandler"]

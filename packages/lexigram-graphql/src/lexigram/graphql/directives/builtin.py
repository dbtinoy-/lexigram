"""Built-in directive handlers for the GraphQL module.

These concrete classes were previously defined in the package
``__init__`` but are now moved here to keep the root lightweight.
"""

from __future__ import annotations

from typing import Any


class DeprecationDirectiveHandler:
    """Marks targets as deprecated using the ``@deprecated`` directive.

    Adds a ``__deprecated__`` attribute with the deprecation reason to any
    target object that supports attribute assignment.
    """

    def apply_directive(
        self,
        directive_name: str,
        args: dict[str, Any],
        target: Any,
    ) -> Any:
        """Apply ``@deprecated`` by setting ``__deprecated__`` on *target*.

        Args:
            directive_name: Expected to be ``"deprecated"``.
            args: May contain ``"reason"`` (str).
            target: Any object.

        Returns:
            The *target* with ``__deprecated__`` set.
        """
        reason = args.get("reason", "No longer supported.")
        try:
            target.__deprecated__ = reason
        except AttributeError:
            pass
        return target

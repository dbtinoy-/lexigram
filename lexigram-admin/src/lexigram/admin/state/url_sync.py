"""URL state synchronization for Lexigram Admin."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
import urllib.parse

if TYPE_CHECKING:
    from lexigram.admin.state.store import Signal


class URLStateManager:
    """Manages synchronization between local state and URL query parameters.

    This allows for deep linking and maintaining UI state across refreshes.
    """

    def __init__(self, base_url: str = "") -> None:
        self.base_url = base_url

    def serialize(self, state: dict[str, Any]) -> str:
        """Serialize state dictionary to a query string."""
        params = {}
        for key, value in state.items():
            if value is None or (isinstance(value, str) and value == ""):
                continue
            params[key] = value

        return urllib.parse.urlencode(params, doseq=True)

    def deserialize(self, query_string: str) -> dict[str, Any]:
        """Deserialize query string back to a state dictionary."""
        params = urllib.parse.parse_qs(query_string.lstrip("?"))
        state = {}

        def _coerce(val) -> Any:
            # Repair stringified lists (URL Bloat Fix)
            if isinstance(val, str) and val.startswith("[") and val.endswith("]"):
                try:
                    import ast

                    parsed = ast.literal_eval(val)
                    if isinstance(parsed, list):
                        return [_coerce(str(i)) for i in parsed]
                except (ValueError, SyntaxError, TypeError):
                    pass

            # Handle numeric/bool
            if val.isdigit():
                return int(val)
            low = val.lower()
            if low == "true":
                return True
            if low == "false":
                return False
            return val

        for key, values in params.items():
            if not values:
                continue

            # Parse each value in the list
            parsed_values = []
            for v in values:
                res = _coerce(v)
                if isinstance(res, list):
                    parsed_values.extend(res)
                else:
                    parsed_values.append(res)

            # Deduplicate
            unique = []
            seen = set()
            for v in parsed_values:
                if v not in seen:
                    unique.append(v)
                    seen.add(v)

            if len(unique) > 1:
                state[key] = unique
            elif unique:
                state[key] = unique[0]

        return state

    def bind_signal(
        self,
        name: str,
        signal: Signal[Any],
        request_query: str | None = None,
    ) -> None:
        """Bind a signal to a URL parameter, initializing it from query if present."""
        if request_query:
            initial_state = self.deserialize(request_query)
            if name in initial_state:
                signal.set(initial_state[name])

        # In a real environment, we'd add a watch(lambda: some_callback(signal.get()))
        # that updates the window.location. This is the structural foundation.

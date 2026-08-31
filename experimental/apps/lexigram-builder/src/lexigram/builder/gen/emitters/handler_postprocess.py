"""Deterministic post-processing for the lexigram-events ``event_handler``
generator.

The handler generator only receives the *handler* name, so its template
renders the subscription method after the handler rather than the event the
handler subscribes to: it emits ``async def on_<handler_name>`` and
``event_name = "<handler_name>"``. The framework's own convention (documented
in the generated docstring and in ``demos/event-driven-orders``) is that
handler methods are named ``on_<event_type>`` — the event the canvas wires to
the handler via the ``event -> event_handler`` edge.

We repair the *generated output* rather than patching the framework
submodule:

* ``event_name = "<handler_snake>"`` is rewritten to the resolved event name
  (used purely for logging inside the generated stub).
* ``async def on_<handler_snake>(`` is renamed to
  ``async def on_<event_snake>(`` so the scaffold provider can subscribe
  ``handler.on_<event>``.

Both rewrites are simple literal substitutions keyed on the handler's file
stem (``<handler_snake>_handler``), so they are safe to apply without
parsing.
"""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True, slots=True)
class HandlerReconcileResult:
    """Result of reconciling a generated event-handler file."""

    text: str
    changed: bool = True


def reconcile_event_handler(
    text: str, *, handler_snake: str, event_snake: str
) -> HandlerReconcileResult:
    """Rewrite the generated handler to name the event it subscribes to."""
    original = text
    text = text.replace(
        f'event_name = "{handler_snake}"',
        f'event_name = "{event_snake}"',
    )
    # Rename every whole-word ``on_<handler>`` occurrence (the method def plus
    # the docstring wiring example) to ``on_<event>``.
    text = re.sub(
        rf"\bon_{re.escape(handler_snake)}\b",
        f"on_{event_snake}",
        text,
    )
    return HandlerReconcileResult(text=text, changed=text != original)

"""Deterministic post-processing for the lexigram-events ``projection``
generator.

The generator emits a projection whose ``handles`` property returns an
empty set — the canvas knows which events a projection consumes via its
``event -> projection`` edges, so the playground fills in the subscribed
event types here (rather than patching the framework template):

* import lines ``from app.events.<snake>_event import <Pascal>Event`` are
  added for each wired event,
* the ``handles`` property's ``return set()`` is rewritten to return the
  set of event classes.

Event class names are derived exactly as the event generator derives them
(``pascal_case`` of the event name + ``Event``).
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from lexigram.contracts.cli.generators import pascal_case, snake_case


@dataclass(frozen=True, slots=True)
class ProjectionReconcileResult:
    """Result of reconciling a generated projection file."""

    text: str
    changed: bool = True


def reconcile_projection(text: str, events: tuple[str, ...]) -> ProjectionReconcileResult:
    """Populate the projection's ``handles`` set with the wired events."""
    original = text
    if not events:
        return ProjectionReconcileResult(text=text, changed=False)

    event_imports = "\n".join(
        f"from app.events.{snake_case(name)}_event import {pascal_case(name)}Event"
        for name in events
    )
    class_names = ", ".join(f"{pascal_case(name)}Event" for name in events)

    # Imports after the framework import block (before the class def).
    text = text.replace(
        "\n\nclass ",
        f"\n\n{event_imports}\n\n\nclass ",
        1,
    )

    # Rewrite the handles body: the generated property returns ``set()``;
    # fill it with the wired event classes.
    text = re.sub(
        r"(\n {8}return )set\(\)",
        rf"\g<1>{{{class_names}}}",
        text,
        count=1,
    )
    return ProjectionReconcileResult(text=text, changed=text != original)

# Events Timeline / Replay Lab

A focused, offline integration contract for **`lexigram-events` + `WebModule`**.

The lab is a small event journal for one deterministic stream. The browser can:

- publish `open`, `approve`, and intentionally failing `fail` events;
- inspect the in-memory event-store history and global sequence numbers;
- observe an event subscriber and a retrying handler failure;
- replay stored history through Lexigram's optional `EventReplayProtocol`; and
- check the lab's readiness, dispatch diagnostics, and offline backend details.

There is no broker, database, worker, or external API. `EventsModule.configure()`
provides the package-owned in-memory event store and event bus; `WebModule`
provides the HTTP and static browser surface. The demo provider only wires these
public package contracts into a scenario.

## Run

From the repository root:

```bash
cd demos/event-timeline
PYTHONPATH=src ../../.venv/bin/python -m timeline_lab
```

Or run the focused contract tests:

```bash
../../.venv/bin/pytest demos/event-timeline/tests -q
```

The standalone port is `8102`. The demo is also listed in Demo Hub as
`/demos/event-timeline/`.

## What to look for

1. Publish several events and note that stream versions and global sequence
   numbers are assigned by the event store.
2. Publish **Simulate handler failure**. The publication result remains an
   enqueue result, while the failure panel reports the handler's retry attempts.
   The projection subscriber still receives the event because the bus continues
   after a failed handler.
3. Press **Replay history**. This uses the store's public
   `EventReplayProtocol` capability and reports the number of events replayed
   without appending duplicates.
4. After a failure probe, the readiness panel becomes degraded and exposes the
   bus's retained asynchronous dispatch error count; successful publication
   remains an enqueue result by design.

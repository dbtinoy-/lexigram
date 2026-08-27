# Spec: Workflow Studio

Slug `workflow-studio` · package `workflow_studio` · port 7080 (`STUDIO_PORT`)
Subsystems: `lexigram-workflow` (sagas, state machine, durable transition history, optimistic locking)

## Story

An order-fulfilment saga renders as a graph: `reserve_stock → charge_card →
ship`. Place an order and watch nodes flip grey→running→green. Inject a
failure at `charge_card`: the node turns red and **compensation flows
backwards** — `release_stock` runs, the saga ends `compensated`. The showstopper:
a "kill engine" button aborts the worker mid-saga; "restart engine" resumes the
exact saga from its last persisted transition — durability you can see.

## Saga definition (scripted, deterministic)

Steps and compensations:

| Step | Action | Compensation |
|---|---|---|
| reserve_stock | decrement seeded inventory | restore it |
| charge_card | mark invoice paid (fails if fault armed) | refund |
| ship | create shipment row | cancel shipment |

Failure injection: per-step arm/disarm; a `crash_after` knob makes the engine
"die" after completing step *k* (process-level state cleared in-memory while
persisted saga history survives in the store).

## Architecture

- `FulfilmentSaga` — declarative step/compensation definitions over the
  workflow package's saga/state-machine services (recon task pins exact
  classes: `WorkflowProvider` registrations).
- `EngineHost` — runs sagas on a single background task queue so kill/restart
  is demonstrable without processes: "kill" cancels the task + drops the
  in-memory runtime; persisted transition log lives in the workflow store;
  "restart" rehydrates pending sagas.
- `SagasController` — API + console pages.

## API

| Route | Purpose |
|---|---|
| `POST /api/sagas {customer}` | start fulfilment saga |
| `POST /api/fault/{step}` / `GET /api/faults` | arm failure per step |
| `POST /api/engine/kill` / `POST /api/engine/restart` | crash & resume demo |
| `GET /api/sagas/{id}` | graph state + transition history (+versions) |
| `GET /api/sagas` | recent sagas with terminal states |

## Console

Top toolbar: New order · fault toggles per step · Kill engine / Restart.
Center: SVG graph of the active saga (node states animate). Right/below:
transition history table — timestamp, from→to, version number ticking.

## Testing

Unit: happy path reaches `completed`; armed failure triggers compensation chain
in reverse order; kill mid-run leaves saga `in_progress` in store; restart
resumes to terminal state exactly once per remaining step. Integration: three
concurrent sagas stay isolated. Console smoke.

## Non-goals

Multi-process distribution; human approval steps (documented as extension);
real payment/inventory integrations.

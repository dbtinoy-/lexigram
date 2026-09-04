# 45 — Dead dashboard widgets: advertise reality, not the catalog (R49)

**Date:** 2026-09-03 · **Status:** shipped · **Roadmap:** dashboard
polish queue ("Live Events Loading…") · **Branch:** `arena/01a05b98-lexigram`

## 1. Problem

In deployments without the events wiring (the playground included) the
dashboard shows **three permanently dead widgets** — Events Throughput,
Dead-Letter Count, Live Events. Each shell polls its render endpoint
every 5 s forever, and every poll swaps in a destructive error card
whose text is a **raw Python repr**:
`WidgetNotFoundError(contributor_name='events', widget_name='live_events')`.
Without JS the skeleton just sits on "Loading…". Root causes:

1. `EventsAdminContributor.get_dashboard_widgets()` returns the static
   `_WIDGETS` catalog unconditionally, even though `on_admin_boot`
   already discovered that none of the three handlers resolve (it logs
   `*_handler_unavailable` and stores `None`).
2. `render_widget_fragment` (lexigram-admin) renders `str(error)` into
   the error card; `WidgetNotFoundError` is a frozen dataclass with no
   `__str__`, so operators get a repr — for *any* contributor, not
   just events.

## 2. Design

### 2.1 Contributor: filter by resolved handlers (lexigram-events)

`get_dashboard_widgets()` returns, **after boot**, only widgets whose
handler actually resolved (name → handler map, the same mapping
`render_widget` dispatches on). **Before boot** the full catalog is
still returned — the declarative view for tooling/tests (the existing
`test_get_dashboard_widgets` asserts exactly this), while live
dashboards (assembled strictly after the mount-time boot) see reality.
This mirrors the platform's own `admin.contributor_disabled` principle:
a feature whose backing service is not registered is *disabled, not
broken*. Routes stay registered (harmless; direct hits get the
friendly card below), nav/health/pages untouched.

### 2.2 Admin: friendly error-card text (defense in depth)

`render_widget_fragment` gains `_friendly_error(error)`:
`WidgetNotFoundError` → "This widget's data source is not available in
this deployment." (isinstance check, contracts import); anything else
keeps `str(error)` but a final guard truncates class-repr-looking
text — no more Python internals in operator-facing cards regardless of
which contributor misbehaves. The structured error still goes to the
log in full, as today.

### 2.3 Out of scope

- Registering the events module in the playground (the fix must hold
  for every deployment shape, not hide behind one).
- The core-contributor widgets and SSE bridge behaviour.

## 3. Implementation order

1. lexigram-events: handler map + post-boot filter + tests (pre-boot
   full catalog, booted-with-nothing → empty, partial resolution →
   partial list; existing suite green).
2. lexigram-admin: `_friendly_error` + tests (repr never rendered,
   friendly text for WidgetNotFoundError, other errors passthrough).
3. Live verify: dashboard no longer contains the three events widget
   shells; direct endpoint hit returns the friendly card.
4. Doc §4 + README row + commit/push (no merge).

## 4. Verification

- **Unit (lexigram-events):** 4 new tests in
  `test_events_contributor.py::TestWidgetAdvertising` — booted with a
  container resolving only the throughput handler → exactly
  `{events_throughput}` advertised; boot with `container=None` → empty
  list; boot with an always-raising container → empty list; direct
  `render_widget("live_events")` still returns the structured
  `WidgetNotFoundError` (the friendly card path). The pre-existing
  `test_get_dashboard_widgets` (un-booted → full catalog of 3) stays
  green, proving the declarative-before-boot semantics. Package suite
  **996 passed / 13 skipped**.
- **Unit (lexigram-admin):** 4 new tests in
  `test_widget_fragment_handler.py::TestFriendlyErrorCards` —
  `WidgetNotFoundError` renders "not available in this deployment"
  with no `WidgetNotFoundError`/`contributor_name=` text in the body;
  a repr-shaped error (`HealthCheckNotFoundError`) is generalised to
  "see the server log"; plain-message errors pass through verbatim;
  `_friendly_error` handles multi-line reprs (DOTALL). Admin suite
  **5788 passed**. Ruff + mypy clean on both packages.
- **Live (playground):** before — dashboard contained 5 mentions each
  of Live Events / Events Throughput / Dead-Letter Count, all polling
  `/admin/events/widgets/*` every 5 s and swapping in
  `WidgetNotFoundError(contributor_name='events', …)`. After restart —
  **0 mentions of any events widget** on the dashboard, and a direct
  hit on `/admin/events/widgets/live_events` returns the friendly
  error card. Full structured error still logged server-side
  (`widget_render_failed` with the repr) for diagnosis.

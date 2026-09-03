# 51 — First-load Toast Overlay Layout (R53) (Full Plan)

**Date:** 2026-09-03 · **Status:** ✅ Implemented · **Branch:**
`arena/01a05b98-lexigram`

## 1. Problem

A successful first navigation can render a flash message in the global
`#flash-container` zone. The dashboard becomes visibly narrower while that
message is present, even though a refresh looks correct after the one-shot
flash has been consumed.

The behavior is especially confusing because it appears to be a dashboard
layout problem rather than a notification problem: the first response changes
the available content width, while the next response does not.

## 2. Root cause

The shell's flash zone is rendered as a sibling of the main content with the
stable ID `#flash-container`. The existing stylesheet only positioned the
client-created `.toast-container` as a fixed overlay. A server-rendered flash
zone therefore remained in normal document flow. Its child toast also had no
bounded width rule for that ID-based zone.

The client-side toast helper separately searched only for `.toast-container`,
so a page with the server-rendered flash zone could create a second container
instead of reusing the global zone.

## 3. Plan

1. Treat both server-rendered `#flash-container` and client-rendered
   `.toast-container` as the same global overlay contract.
2. Remove both containers from layout flow with `position: fixed`.
3. Bound the overlay and its toast to the viewport so long messages cannot
   create horizontal overflow.
4. Keep the overlay transparent to pointer events outside the toast itself.
5. Make client-created toasts reuse the flash zone when it is present.
6. Add a regression guard for fixed positioning, width bounding, and pointer
   behavior; verify a first-load flash and a no-flash refresh path.

## 4. Implementation

- `admin.css` now shares the fixed top-right overlay rule between
  `.toast-container` and `#flash-container`.
- The shared rule bounds the zone to `min(360px, calc(100vw - 2rem))`, while
  direct child toasts use `width: 100%`, `min-width: 0`, and
  `box-sizing: border-box`.
- The zone uses `pointer-events: none`; direct toast children restore
  `pointer-events: auto`, so an empty overlay cannot block dashboard controls.
- `admin.js` now resolves either `.toast-container` or `#flash-container`
  before creating a new container.
- The shell toast regression suite checks the CSS contract so a future
  selector rename cannot reintroduce the first-load width shift.

## 5. Verification

- `tests/unit/ui/test_shell_toasts.py` passes, including the fixed overlay
  regression (5 passed).
- The admin package suite passes from its package root (6,091 passed, 34
  skipped), including the default skipped-e2e collection.
- The first-run e2e scenario passes with `--run-e2e` (2 passed) and exits
  cleanly.
- The UI package suite passes (1,452 passed, 78 skipped), and the changed
  JavaScript passes Node syntax validation.
- Manual/live follow-up: inspect the dashboard with a successful flash present,
  dismiss it or allow auto-dismiss, then refresh. The dashboard content width
  must remain identical in all three states; only the overlay should change.

## 6. Acceptance criteria

- [x] A first-load flash never participates in dashboard layout flow.
- [x] Toast width is bounded on desktop and narrow viewports.
- [x] The empty flash zone does not block interaction outside a toast.
- [x] Server- and client-created toasts share one global container.
- [x] A regression test protects the CSS contract.
- [ ] Live playground/browser confirmation is performed in the next resumed
      live-verification step.

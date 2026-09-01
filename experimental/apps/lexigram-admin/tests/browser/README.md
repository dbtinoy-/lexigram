# Browser tests

Playwright tests for behaviour that only exists once a real engine has
parsed the document — dirty-form tracking, the unsaved-changes guard,
submit locking, and HTMX swap handling. None of it is reachable from an
HTTP-level test.

## Running

Browser tests are opt-in and skipped by default, so a contributor without
browser binaries still gets a green run:

```bash
# one-time
uv run playwright install chromium

# run them
uv run pytest experimental/apps/lexigram-admin/tests/browser --run-browser
```

Without `--run-browser` the suite is collected and skipped. With the flag
but no browser installed, each test skips with the exact install command
rather than failing.

## How the harness works

`conftest.py` provides three fixtures:

- **`live_server`** — a factory taking an ASGI app and returning its base
  URL. It binds port 0, waits for the socket to accept connections, and
  shuts the server down afterwards. Tests never hardcode a port, so they
  are safe to run in parallel.
- **`browser_type`** — a session-scoped headless Chromium.
- **`page`** — a page in a fresh browser context per test, so cookies and
  storage never leak between tests.

The earlier Playwright tests in `tests/e2e/` expected an operator to start
a server by hand on a fixed port and skipped silently when nothing was
listening, which meant they never ran. This harness owns the server
lifecycle instead.

Those two files (`test_sidebar_htmx.py` and
`test_sidebar_htmx_login_contents.py`) have been removed. Besides never
running, they navigated to a `first_aid_topics` resource that exists
nowhere in this codebase, and one referenced `resp` before assignment and
drove `page` after closing its browser — it would have raised rather than
asserted. Their intent is now covered by `test_sidebar_navigation.py`
against a self-hosted app.

## Test files

- **`test_harness.py`** — browser-free checks of the fixtures themselves.
- **`test_form_behavior.py`** — dirty-form tracking, unsaved-changes
  guard, submit locking.
- **`test_sidebar_navigation.py`** — HTMX sidebar swaps: in-place update,
  no full reload, pushed URL, fragment-vs-full-page responses, and the
  back button.

Pages under test load the **vendored** `static/js/htmx.min.js` rather than
a CDN URL, so the suite needs no network access and exercises the asset
the admin actually ships.

`test_harness.py` exercises the server fixture over plain HTTP with no
browser involved. It runs everywhere, so if the harness breaks, that shows
up as a failure rather than as a suite that quietly skips.

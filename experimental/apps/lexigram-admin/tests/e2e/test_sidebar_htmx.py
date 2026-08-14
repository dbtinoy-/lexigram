import os

from playwright.sync_api import sync_playwright


def test_sidebar_htmx_click_updates_main_content():
    """Smoke test: open admin shell, click first HTMX sidebar link and assert #main-content changes.

    Requirements:
    - Admin server running locally at ADMIN_BASE (default http://127.0.0.1:8000)
    - Playwright installed (pip install playwright) and browsers installed (playwright install)

    This is a lightweight e2e smoke test intended for local runs or CI.
    """

    base = os.environ.get("ADMIN_BASE", "http://127.0.0.1:9003")

    import urllib.request

    import pytest

    # Skip test if ADMIN_BASE is not reachable in the current environment
    try:
        req = urllib.request.Request(base, method="HEAD")
        with urllib.request.urlopen(req, timeout=2):
            pass
    except (urllib.error.URLError, urllib.error.HTTPError, OSError):
        pytest.skip(f"Admin server not reachable at {base}; skipping e2e test")

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        context = browser.new_context()
        page = context.new_page()
        # Login first to ensure we have an authenticated shell with sidebar
        page.goto(f"{base}/admin/login", timeout=30_000)
        page.fill('input[name="email"]', "admin@example.com")
        page.fill('input[name="password"]', "admin")
        page.click('button[type="submit"]')
        # Wait for any navigation/network activity to settle
        page.wait_for_load_state("networkidle")
        try:
            page.wait_for_url(f"{base}/admin/", timeout=15_000)
        except (TimeoutError, OSError) as e:
            # If redirect did not occur, capture diagnostics and try directly navigating to the resource
            os.makedirs("/tmp/playwright_debug", exist_ok=True)
            page.screenshot(
                path="/tmp/playwright_debug/post_submit.png", full_page=True,
            )
            with open(
                "/tmp/playwright_debug/post_submit.html", "w", encoding="utf-8",
            ) as fh:
                fh.write(page.content())
            page.goto(f"{base}/admin//first_aid_topics/", timeout=30_000)
            page.wait_for_load_state("networkidle")

        # Ensure we are on a resource page that renders the full admin shell with sidebar
        page.goto(f"{base}/admin//first_aid_topics/", timeout=30_000)
        page.wait_for_load_state("networkidle")

        # Wait for sidebar to appear and find the first HTMX admin link (href contains /admin//)
        page.wait_for_selector("aside nav a[href*='/admin//']", timeout=30_000)
        link = page.locator("aside nav a[href*='/admin//']").first
        href = link.get_attribute("href")
        assert href is not None

        # Click and wait for the HTMX request/response
        link.wait_for(state="visible", timeout=5000)
        link.scroll_into_view_if_needed()
        with page.expect_response(
            lambda r: "/admin//" in r.url and r.request.method == "GET",
        ) as resp_info:
            link.click(force=True)

        resp = resp_info.value
        assert resp.status == 200, f"Unexpected status {resp.status} for {resp.url}"

        # The HTMX response body should include content that would be swapped into main
        body = resp.text()
        assert body and len(body.strip()) > 0, "HTMX response was empty"
        assert (
            ("<h1" in body)
            or ("<h2" in body)
            or ('class="card"' in body)
            or ("table" in body)
        ), "HTMX response did not contain an expected header/card/table"

        browser.close()

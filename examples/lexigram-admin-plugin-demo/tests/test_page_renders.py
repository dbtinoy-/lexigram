from __future__ import annotations

from demo.pages.overview import OverviewPage


async def test_overview_page_returns_page_response() -> None:
    page = OverviewPage()
    response = await page.view(request=None)
    assert response.title == "Plugin Overview"
    assert response.content is not None


async def test_overview_page_contains_expected_html() -> None:
    page = OverviewPage()
    response = await page.view(request=None)
    assert "<h2>Demo Plugin</h2>" in response.content
    assert "custom management page" in response.content


async def test_overview_page_has_correct_title_attribute() -> None:
    assert OverviewPage.title == "Plugin Overview"


async def test_overview_page_has_correct_path() -> None:
    assert OverviewPage.path == "/admin/demo/overview"

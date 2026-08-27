"""Tests — real composition root, no mocks.

Every test boots a real Application with the actual DI container.
Services are tested through their public API, not by mocking internals.
"""

from __future__ import annotations

import pytest
import httpx


class TestContentGenerator:
    """Test content generation through the service layer."""

    @pytest.mark.asyncio
    async def test_generate_content(self, client: httpx.AsyncClient) -> None:
        """POST /api/content/generate returns generated content."""
        resp = await client.post(
            "/api/content/generate",
            json={"topic": "AI assistants", "style": "professional"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "content" in data
        assert data["topic"] == "AI assistants"
        assert data["style"] == "professional"

    @pytest.mark.asyncio
    async def test_generate_missing_topic(self, client: httpx.AsyncClient) -> None:
        """POST /api/content/generate with empty topic returns error."""
        resp = await client.post(
            "/api/content/generate",
            json={"topic": ""},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data

    @pytest.mark.asyncio
    async def test_generate_variations(self, client: httpx.AsyncClient) -> None:
        """POST /api/content/variations returns multiple variations."""
        resp = await client.post(
            "/api/content/variations",
            json={"topic": "AI assistants", "count": 2},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "variations" in data
        assert len(data["variations"]) == 2


class TestProductExtractor:
    """Test product extraction through the service layer."""

    @pytest.mark.asyncio
    async def test_extract_product(self, client: httpx.AsyncClient) -> None:
        """POST /api/content/extract returns structured product data."""
        resp = await client.post(
            "/api/content/extract",
            json={"description": "A wireless mouse with ergonomic design"},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "product" in data

    @pytest.mark.asyncio
    async def test_extract_missing_description(self, client: httpx.AsyncClient) -> None:
        """POST /api/content/extract with empty description returns error."""
        resp = await client.post(
            "/api/content/extract",
            json={"description": ""},
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "error" in data


class TestHealth:
    """Test health endpoint."""

    @pytest.mark.asyncio
    async def test_health(self, client: httpx.AsyncClient) -> None:
        """GET /api/content/health returns ok."""
        resp = await client.get("/api/content/health")
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "ok"

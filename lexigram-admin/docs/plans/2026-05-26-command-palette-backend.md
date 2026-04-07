# Command Palette Backend Implementation Plan

> **For agentic workers:** Subagent-driven development. Steps use checkbox (`- [ ]`) syntax.

**Goal:** Wire the existing CommandPalette Alpine.js frontend to a backend endpoint so user typing shows dynamic search results alongside static navigation commands.

**Architecture:** A `CommandPaletteController` returns JSON at `GET /admin/command-palette?q=`. The Alpine.js component fetches this on keystroke (debounced), merges with static commands, and displays results. No HTMX — JSON fetch directly to Alpine.

**Existing context:**
- `CommandPalette` in `ui/organisms/command_palette.py` — Alpine.js component with 4 hardcoded commands
- `SearchService` in `services/search_service.py` — already has `search(query)` returning `SearchResults`
- `SearchController` in `controllers/search.py` — reference pattern for controller
- `shell.py:393` renders `CommandPalette` as part of AdminShell
- Topbar search pill dispatches `open-command-palette` event (but no listener exists)
- Route wiring in `core/routing.py:131-143` for search — reference pattern

---

### Task 1: Write tests for CommandPaletteController

**Files:**
- Create: `tests/unit/controllers/test_command_palette_controller.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for CommandPaletteController."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest
from starlette.datastructures import QueryParams
from starlette.requests import Request

from lexigram.admin.controllers.command_palette import CommandPaletteController
from lexigram.admin.services.search_service import SearchResult, SearchResults


class TestCommandPaletteController:
    @pytest.fixture
    def mock_search_service(self):
        service = MagicMock()
        service.search = AsyncMock(return_value=SearchResults(
            query="alice",
            total_count=1,
            results=[
                SearchResult(
                    resource_name="users",
                    resource_label="Users",
                    id="1",
                    title="Alice",
                    subtitle="alice@example.com",
                    url="/admin/users/1",
                ),
            ],
            resource_counts={"users": 1},
        ))
        return service

    @pytest.fixture
    def controller(self, mock_search_service):
        return CommandPaletteController(search_service=mock_search_service)

    @pytest.mark.asyncio
    async def test_search_returns_json(self, controller, mock_search_service):
        request = MagicMock(spec=Request)
        request.query_params = QueryParams(q="alice")
        response = await controller.search(request)
        assert response.status_code == 200
        assert response.headers.get("content-type") == "application/json"

    @pytest.mark.asyncio
    async def test_search_returns_commands(self, controller, mock_search_service):
        request = MagicMock(spec=Request)
        request.query_params = QueryParams(q="alice")
        response = await controller.search(request)
        commands = response.body
        assert isinstance(commands, list)
        assert len(commands) > 0
        for cmd in commands:
            assert "label" in cmd
            assert "href" in cmd or "action" in cmd

    @pytest.mark.asyncio
    async def test_search_includes_dynamic_results(self, controller, mock_search_service):
        request = MagicMock(spec=Request)
        request.query_params = QueryParams(q="alice")
        response = await controller.search(request)
        commands = response.body
        dynamic = [c for c in commands if c.get("label", "").startswith("Users:")]
        assert len(dynamic) == 1
        assert dynamic[0]["href"] == "/admin/users/1"

    @pytest.mark.asyncio
    async def test_search_static_without_query(self, controller, mock_search_service):
        request = MagicMock(spec=Request)
        request.query_params = QueryParams(q="")
        response = await controller.search(request)
        commands = response.body
        labels = [c["label"] for c in commands]
        assert "Go to Dashboard" in labels
        assert "Manage Users" in labels
        assert "Settings" in labels
        # No dynamic results when no query
        mock_search_service.search.assert_not_called()

    @pytest.mark.asyncio
    async def test_short_query_skips_search(self, controller, mock_search_service):
        request = MagicMock(spec=Request)
        request.query_params = QueryParams(q="a")
        response = await controller.search(request)
        mock_search_service.search.assert_not_called()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest lexigram-admin/tests/unit/controllers/test_command_palette_controller.py -v --tb=short -W ignore::DeprecationWarning`
Expected: FAIL with "ModuleNotFoundError: No module named 'lexigram.admin.controllers.command_palette'"

---

### Task 2: Implement CommandPaletteController

**Files:**
- Create: `src/lexigram/admin/controllers/command_palette.py`

- [ ] **Step 1: Write the controller**

```python
"""Controller for the command palette endpoint."""
from __future__ import annotations

from typing import Any

from starlette.requests import Request
from starlette.responses import JSONResponse

from lexigram.admin.services.search_service import SearchService
from lexigram.di.decorators import inject
from lexigram.logging import get_logger

logger = get_logger(__name__)

_STATIC_COMMANDS: list[dict[str, Any]] = [
    {"label": "Go to Dashboard", "href": "/admin/", "icon": "home", "shortcut": "G D"},
    {"label": "Manage Users", "href": "/admin/users", "icon": "users", "shortcut": "G U"},
    {"label": "Toggle Dark Mode", "action": "darkMode = !darkMode", "icon": "moon", "shortcut": "T D"},
    {"label": "Settings", "href": "#", "icon": "settings", "shortcut": ","},
]

_MIN_QUERY_LENGTH = 2


@inject
class CommandPaletteController:
    """Handles the command palette search endpoint.

    Returns JSON commands that the frontend merges with static commands.
    """

    def __init__(self, search_service: SearchService) -> None:
        self._search_service = search_service

    async def search(self, request: Request) -> JSONResponse:
        """Handle GET /admin/command-palette?q=..."""
        query = (request.query_params.get("q") or "").strip()
        commands: list[dict[str, Any]] = []

        # Filter static commands by query
        for cmd in _STATIC_COMMANDS:
            if not query or query.lower() in cmd["label"].lower():
                commands.append(cmd)

        # Dynamic search results from backend
        if len(query) >= _MIN_QUERY_LENGTH:
            try:
                results = await self._search_service.search(query)
                for r in results.results:
                    commands.append({
                        "label": f"{r.resource_label}: {r.title}",
                        "href": r.url,
                        "icon": "search",
                        "subtitle": r.subtitle,
                    })
            except Exception:
                logger.exception("Command palette search failed for query=%s", query)

        return JSONResponse(commands)
```

- [ ] **Step 2: Run test to verify it passes**

Run: `uv run pytest lexigram-admin/tests/unit/controllers/test_command_palette_controller.py -v --tb=short -W ignore::DeprecationWarning`
Expected: PASS

- [ ] **Step 3: Run full test suite to verify no regressions**

Run: `uv run pytest lexigram-admin/tests/ -x --tb=short -W ignore::DeprecationWarning`
Expected: ALL PASS

---

### Task 3: Wire command palette route

**Files:**
- Modify: `core/routing.py` (add route)

- [ ] **Step 1: Add route in routing.py**

In `core/routing.py`, after the search route import and wiring:

```python
from lexigram.admin.controllers.command_palette import CommandPaletteController
```

In the `_build_list_routes` method (or equivalent route building), add:

```python
# Command palette
palette_controller = CommandPaletteController(search_service=search_service)
routes.append(
    Route(
        "/command-palette",
        endpoint=palette_controller.search,
        methods=["GET"],
        name="admin_command_palette",
    )
)
```

Note: `search_service` is already instantiated in this method for `SearchController`.

- [ ] **Step 2: Run test to verify route works**

Run: `uv run pytest lexigram-admin/tests/ -x --tb=short -W ignore::DeprecationWarning`
Expected: ALL PASS

---

### Task 4: Enhance frontend Alpine.js component

**Files:**
- Modify: `src/lexigram/admin/ui/organisms/command_palette.py`

- [ ] **Step 1: Update CommandPalette Alpine component to fetch from backend**

Replace the inline `<script>` block's Alpine.data registration to include:

```javascript
get filteredCommands() {
    return this.commands;
},
async fetchResults(query) {
    if (query.length < 2) {
        this.commands = this.staticCommands;
        return;
    }
    try {
        const response = await fetch(`/admin/command-palette?q=${encodeURIComponent(query)}`);
        const data = await response.json();
        this.commands = data;
    } catch (e) {
        this.commands = this.staticCommands;
    }
},
```

And add debounce + watch on `search`:

```javascript
search: '',
searchTimeout: null,
watch: {
    search(value) {
        clearTimeout(this.searchTimeout);
        this.selectedIndex = 0;
        this.searchTimeout = setTimeout(() => {
            this.fetchResults(value);
        }, 200);
    }
},
```

Also add listener for `open-command-palette` event:
```python
"x-on:open-command-palette.window": "toggle()",
```

- [ ] **Step 2: Verify the component renders without errors**

Run: `uv run pytest lexigram-admin/tests/unit/ui/ -x -q --tb=short -W ignore::DeprecationWarning`
Expected: ALL PASS

---

### Task 5: Verify end-to-end

- [ ] **Step 1: Run full test suite**

Run: `uv run pytest lexigram-admin/tests/ -q --tb=short -W ignore::DeprecationWarning`
Expected: ALL PASS

- [ ] **Step 2: Run ruff + mypy**

Run: `uv run ruff check lexigram-admin/ && uv run mypy lexigram-admin/src/lexigram/admin/controllers/command_palette.py`
Expected: No errors

- [ ] **Step 3: Commit**

```bash
git add -A lexigram-admin/
git commit -m "feat(admin): command palette backend endpoint + Alpine dynamic fetch

CommandPaletteController at GET /admin/command-palette?q= returns JSON
commands merging static navigation with dynamic search results.
Alpine.js component enhanced to fetch from backend on keystroke
(debounced 200ms). open-command-palette event listener wired."
```

# Global Search Implementation Plan

## Architecture

```
TopBar / Header search pill
    ↓ dispatches 'open-command-palette' / HTMX GET /admin/search?q=...
    ↓
SearchController (new: controllers/search.py)
    ↓ calls SearchService
    ↓
SearchService (new: services/search_service.py)
    ↓ iterates Resource classes, calls Resource.search()
    ↓
Search UI component renders results
    ↓ swappped into CommandPalette / search-results zone
```

## Files to Create

### 1. `services/search_service.py`
- `SearchResult` dataclass: `resource_name`, `resource_label`, `id`, `title`, `subtitle`, `url`
- `SearchService` class with `search(query: str, limit: int = 5)` method
- Discovers resources from ResourceManager or registry
- Calls `Resource.search()` per resource
- Aggregates and ranks results

### 2. `controllers/search.py`
- `SearchController` with `search_get(request)` handler
- Reads `q` param from request
- Calls `SearchService.search(q)`
- Returns HTML response with search results

### 3. `core/routing.py` update
- Add `/admin/search` route pointing to SearchController

### 4. Search results template/component
- Renders search results as clickable items with resource label, title, subtitle

## Files to Modify

### 5. `ui/organisms/command_palette.py` (or topbar/header)
- Wire CommandPalette to show dynamic search results from backend
- Header search input already points to `/admin/search` — just need to ensure handler exists

## Test Strategy

- `SearchService` unit tests: mock resources, verify aggregation
- `SearchController` integration test: verify route handler
- End-to-end: wire through CommandPalette

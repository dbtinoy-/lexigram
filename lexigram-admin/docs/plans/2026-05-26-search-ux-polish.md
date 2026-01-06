# Search UX Polish Plan

**Goal:** Add keyboard navigation, result count, and loading state to the multi-resource global search.

**Files:**
- Modify: `lexigram-admin/src/lexigram/admin/controllers/search.py`
- Modify: `lexigram-admin/src/lexigram/admin/ui/templates/shell.py`

---

### Task 1: Add result count header to search results

**File:** `controllers/search.py`

In `_render_results()`, after the opening `<div class="search-results ...">` tag, add:

```python
count_text = f"{results.total_count} result{'s' if results.total_count != 1 else ''} across {results.group_count} resource{'s' if results.group_count != 1 else ''}"
```

Add before the sections:
```python
sections.insert(0, (
    '<div class="search-summary px-4 py-2 text-xs text-gray-400 dark:text-gray-500 border-b border-gray-100 dark:border-gray-700/50">'
    f"{count_text}"
    "</div>"
))
```

### Task 2: Add keyboard navigation and loading state to shell

**File:** `ui/templates/shell.py`

In the existing `<script>` block in `search_overlay`, enhance the click-away handler to also:
1. Track currently focused result index
2. Handle arrow up/down to move focus
3. Handle Enter to navigate to focused result
4. Handle Escape to close

Also add an HTMX `htmx:before-request` / `htmx:after-request` handler to show/ hide a loading indicator inside `#search-results`.

### Task 3: Test

```bash
uv run pytest lexigram-admin/tests/ --tb=short -q --no-header | tail -5
```

"""Client-side script/markup builders for AdminShell."""

from __future__ import annotations

from typing import Any

from lexigram.ui import raw


def search_overlay_markup() -> Any:
    """Build the search-overlay styles, keyboard nav script and SPA nav hook."""
    return raw(
        """
        <style>
            [x-cloak] {
                display: none !important;
            }
            #search-results {
                position: fixed;
                top: 64px;
                left: 50%;
                transform: translateX(-50%);
                width: 90%;
                max-width: 640px;
                z-index: 45;
                pointer-events: none;
            }
            #search-results > * {
                pointer-events: auto;
            }
            .search-subtitle {
                display: block;
                font-size: 0.75rem;
                color: var(--muted-foreground);
                margin-top: 0.125rem;
            }
            .search-result-item:focus-visible {
                outline: 2px solid var(--ring);
                outline-offset: -2px;
            }
            @media (max-width: 640px) {
                #search-results {
                    top: 56px;
                    width: 95%;
                }
            }
        </style>
        <script>
            (function() {
                if (window.__adminShellSearchInit) return;
                window.__adminShellSearchInit = 1;
                var searchResults = document.getElementById('search-results');
                var searchFocusedIndex = -1;

            document.addEventListener('click', function(e) {
                var results = document.getElementById('search-results');
                if (!results) return;
                var searchInput = document.querySelector('[hx-get*="/admin/search"]');
                if (results.children.length > 0 &&
                    !results.contains(e.target) &&
                    (!searchInput || !searchInput.contains(e.target))) {
                    results.innerHTML = '';
                    searchFocusedIndex = -1;
                }
            });

            document.addEventListener('keydown', function(e) {
                var results = document.getElementById('search-results');
                if (!results || results.children.length === 0) return;

                var items = results.querySelectorAll('.search-result-item');
                if (items.length === 0) return;

                // Escape closes search
                if (e.key === 'Escape') {
                    results.innerHTML = '';
                    searchFocusedIndex = -1;
                    return;
                }

                // Arrow down
                if (e.key === 'ArrowDown') {
                    e.preventDefault();
                    searchFocusedIndex = Math.min(searchFocusedIndex + 1, items.length - 1);
                    items[searchFocusedIndex].focus();
                    return;
                }

                // Arrow up
                if (e.key === 'ArrowUp') {
                    e.preventDefault();
                    searchFocusedIndex = Math.max(searchFocusedIndex - 1, 0);
                    items[searchFocusedIndex].focus();
                    return;
                }
            });

            // Loading indicator via HTMX events
            document.addEventListener('htmx:beforeRequest', function(e) {
                var searchInput = e.detail?.elt?.closest('[hx-get*="/admin/search"]');
                if (!searchInput) return;
                var results = document.getElementById('search-results');
                if (!results) return;
                results.innerHTML = '<div class="search-loading text-center py-8 px-4 text-sm text-muted-foreground">Searching...</div>';
                searchFocusedIndex = -1;
            });

            document.addEventListener('htmx:afterRequest', function(e) {
                var searchInput = e.detail?.elt?.closest('[hx-get*="/admin/search"]');
                if (!searchInput) return;
                var results = document.getElementById('search-results');
                if (!results) return;
                if (!results.querySelector('.search-results, .search-results-empty')) {
                    results.innerHTML = '';
                }
            });

            document.addEventListener('htmx:beforeSwap', function(e) {
                var searchInput = e.detail?.elt?.closest('[hx-get*="/admin/search"]');
                if (searchInput) {
                    searchFocusedIndex = -1;
                }
            });

            // SPA navigation: intercept plain same-origin link clicks and
            // swap the full page response into the body. Handled here via
            // document-level delegation so it survives body swaps.
            document.addEventListener('click', function(e) {
                if (e.defaultPrevented || e.button !== 0) return;
                if (e.metaKey || e.ctrlKey || e.shiftKey || e.altKey) return;
                var el = e.target instanceof Element ? e.target.closest('a[href]') : null;
                if (!el) return;
                if (el.getAttribute('target') === '_blank' || el.hasAttribute('download')) return;
                if (el.hasAttribute('hx-get') || el.hasAttribute('hx-post') || el.hasAttribute('hx-delete')) return;
                var href = el.getAttribute('href');
                if (!href || href.startsWith('#')) return;
                var url;
                try { url = new URL(el.href, location.href); } catch (err) { return; }
                if (url.origin !== location.origin) return;
                e.preventDefault();
                if (window.htmx) {
                    // Abort stale in-flight widget loads — they belong to the
                    // page we are leaving and would otherwise hold browser
                    // connection slots until the swap completes.
                    document.querySelectorAll('.widget-body[hx-get]').forEach(function(w) {
                        w.dispatchEvent(new Event('htmx:abort', { bubbles: true }));
                    });
                    window.htmx.ajax('GET', url.href, { target: 'body', swap: 'innerHTML' });
                } else {
                    location.href = url.href;
                }
                window.scrollTo(0, 0);
            });
            })();
        </script>
        """,
    )


def loading_bar_script(flash_zone_id: str) -> Any:
    """Build the global HTMX loading indicator and error-handling scripts.

    Args:
        flash_zone_id: DOM id of the flash container used for error toasts.
    """
    return raw(
        f"""
        <div id="htmx-loading-bar" class="hidden fixed top-0 left-0 right-0 h-1 bg-primary-600 z-50 transition-opacity">
            <div class="h-full bg-primary-400 animate-pulse"></div>
        </div>
        <script>
            (function() {{
                if (window.__adminShellInit) return;
                window.__adminShellInit = 1;
                // Apply the sidebar width class synchronously on first
                // load so the shell paints at the right width before
                // Alpine's deferred scripts start. Also pre-inject the
                // width utility rules: the Tailwind CDN regenerates its
                // stylesheet after htmx body swaps and would not have
                // these rules at swap time, flashing the sidebar at
                // auto width until it re-scans.
                var sideWidthStyle = document.createElement('style');
                sideWidthStyle.textContent = '.w-24 {{ width: 6rem; }} .w-72 {{ width: 18rem; }}';
                document.head.appendChild(sideWidthStyle);
                var aside = document.getElementById('main-sidebar');
                if (aside) {{
                    aside.classList.add(localStorage.getItem('sidebarMini') === 'true' ? 'w-24' : 'w-72');
                }}
                // Loading bar
            document.body.addEventListener('htmx:beforeRequest', function(e) {{
                document.getElementById('htmx-loading-bar').classList.remove('hidden');

                // Cleanup filter storage on full page/resource navigation
                if (e.detail && e.detail.target && e.detail.target.id === 'main-content') {{
                    Object.keys(localStorage).forEach(function(key) {{
                        if (key.startsWith('lexigram_filter_') && key !== 'lexigram_filter_drawer_open') {{
                            localStorage.removeItem(key);
                        }}
                    }});
                }}
            }});
            document.body.addEventListener('htmx:afterRequest', function() {{
                document.getElementById('htmx-loading-bar').classList.add('hidden');
            }});

            // Body swaps can leave Alpine components partially initialized
            // (bindings registered but effects never run) because Alpine's
            // observer and this initTree race each other through the same
            // directive deferral queue. Wait for the observer to settle,
            // then run initTree — it can only be safely re-run on a scoped
            // subtree, not the whole body (see below). Only run on full
            // body swaps, not widget fragment swaps.
            document.body.addEventListener('htmx:afterSwap', function(evt) {{
                if (evt.detail && evt.detail.elt !== document.body) return;
                setTimeout(function() {{
                    try {{
                        // Scope the re-init to the swapped content region
                        // only. Alpine's initTree is not idempotent: it
                        // re-registers every directive it walks, and
                        // re-initializing the shell chrome (x-for
                        // templates like the notification list) a second
                        // time leaves duplicate cleanups behind, so the
                        // second cleanup run throws (x-for reads
                        // _x_lookup after the first cleanup deleted it).
                        var mainContent = document.getElementById('main-content');
                        if (mainContent && window.Alpine) window.Alpine.initTree(mainContent);
                    }} catch (err) {{ /* noop: initTree is best-effort */ }}
                }}, 200);
            }});

            // htmx's handleAttributes restore step runs right before
            // htmx:afterSettle and resets each node with an id back to
            // its pristine server markup -- which wipes the width class
            // Alpine's x-bind effect applied to the sidebar. Re-running
            // the aside's own effects restores the class through Alpine's
            // bookkeeping, so the mini-mode toggle keeps working.
            document.body.addEventListener('htmx:afterSettle', function(evt) {{
                if (evt.detail && evt.detail.elt !== document.body) return;
                var aside = document.getElementById('main-sidebar');
                if (aside && aside._x_runEffects) {{
                    aside._x_runEffects();
                }}
            }});

            // Error handling for HTMX requests
            document.body.addEventListener('htmx:responseError', function(evt) {{
                const {{ xhr }} = evt.detail;
                const status = xhr.status;
                const flashContainer = document.getElementById('{flash_zone_id}');

                let message = 'An error occurred';
                let variant = 'error';

                if (status === 403) {{
                    message = 'Permission denied. You may need to log in again.';
                }} else if (status === 404) {{
                    message = 'The requested resource was not found.';
                }} else if (status === 422) {{
                    message = 'Please check your input and try again.';
                    variant = 'warning';
                }} else if (status === 429) {{
                    message = 'Too many requests. Please wait and try again.';
                    variant = 'warning';
                }} else if (status >= 500) {{
                    message = 'Server error. Please try again later.';
                }}

                // Display toast notification
                if (flashContainer) {{
                    flashContainer.innerHTML = `<div class="fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg bg-destructive/10 border border-destructive/30 text-destructive max-w-sm" role="alert">
                        <div class="flex items-start gap-3">
                            <svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z" clip-rule="evenodd"></path></svg>
                            <div class="flex-1">
                                <p class="font-medium">Error</p>
                                <p class="text-sm mt-1">${{message}}</p>
                            </div>
                            <button onclick="this.closest('[role=alert]').remove()" class="text-destructive hover:text-destructive"><svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg></button>
                        </div>
                    </div>`;
                    // Auto-dismiss after 5 seconds
                    setTimeout(() => {{ if (flashContainer.firstChild) flashContainer.innerHTML = ''; }}, 5000);
                }}
            }});

            // Show toast helper
            function showToast(message, type) {{
                const flashContainer = document.getElementById('{flash_zone_id}');
                if (!flashContainer) return;
                const bgColors = {{success: 'bg-success/10 border border-success/30 text-success', error: 'bg-destructive/10 border border-destructive/30 text-destructive', warning: 'bg-warning/10 border border-warning/30 text-warning', info: 'bg-info/10 border border-info/30 text-info'}};
                const icons = {{success: 'M16.707 5.293a1 1 0 010 1.414l-8 8a1 1 0 01-1.414 0l-4-4a1 1 0 011.414-1.414L8 12.586l7.293-7.293a1 1 0 011.414 0z', error: 'M10 18a8 8 0 100-16 8 8 0 000 16zM8.707 7.293a1 1 0 00-1.414 1.414L8.586 10l-1.293 1.293a1 1 0 101.414 1.414L10 11.414l1.293 1.293a1 1 0 001.414-1.414L11.414 10l1.293-1.293a1 1 0 00-1.414-1.414L10 8.586 8.707 7.293z', warning: 'M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z', info: 'M18 10a8 8 0 11-16 0 8 8 0 0116 0zm-7-4a1 1 0 11-2 0 1 1 0 012 0zM9 9a1 1 0 000 2v3a1 1 0 001 1h1a1 1 0 100-2v-3a1 1 0 00-1-1H9z'}};
                const colorClass = bgColors[type] || bgColors.info;
                const iconPath = icons[type] || icons.info;
                const labels = {{success: 'Success', error: 'Error', warning: 'Warning', info: 'Info'}};
                flashContainer.innerHTML = `<div class="fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg ${{colorClass}} border max-w-sm" role="alert">
                    <div class="flex items-start gap-3">
                        <svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="${{iconPath}}" clip-rule="evenodd"></path></svg>
                        <div class="flex-1">
                            <p class="font-medium">${{labels[type] || 'Info'}}</p>
                            <p class="text-sm mt-1">${{message}}</p>
                        </div>
                        <button onclick="this.closest('[role=alert]').remove()" class="opacity-60 hover:opacity-100"><svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg></button>
                    </div>
                </div>`;
                setTimeout(() => {{ if (flashContainer.firstChild) flashContainer.innerHTML = ''; }}, 5000);
            }}

            // Listen for show-toast custom event (fired via HX-Trigger)
            document.body.addEventListener('show-toast', function(evt) {{
                var detail = evt.detail;
                showToast(detail.message || 'Success', detail.type || 'success');
            }});

            // Network error handling
            document.body.addEventListener('htmx:sendError', function(evt) {{
                const flashContainer = document.getElementById('{flash_zone_id}');
                if (flashContainer) {{
                    flashContainer.innerHTML = `<div class="fixed top-4 right-4 z-50 p-4 rounded-lg shadow-lg bg-warning/10 border border-warning/30 text-warning max-w-sm" role="alert">
                        <div class="flex items-start gap-3">
                            <svg class="w-5 h-5 flex-shrink-0" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M8.257 3.099c.765-1.36 2.722-1.36 3.486 0l5.58 9.92c.75 1.334-.213 2.98-1.742 2.98H4.42c-1.53 0-2.493-1.646-1.743-2.98l5.58-9.92zM11 13a1 1 0 11-2 0 1 1 0 012 0zm-1-8a1 1 0 00-1 1v3a1 1 0 002 0V6a1 1 0 00-1-1z" clip-rule="evenodd"></path></svg>
                            <div class="flex-1">
                                <p class="font-medium">Network Error</p>
                                <p class="text-sm mt-1">Unable to connect. Check your internet connection.</p>
                            </div>
                            <button onclick="this.closest('[role=alert]').remove()" class="text-warning hover:text-warning/90"><svg class="w-4 h-4" fill="currentColor" viewBox="0 0 20 20"><path fill-rule="evenodd" d="M4.293 4.293a1 1 0 011.414 0L10 8.586l4.293-4.293a1 1 0 111.414 1.414L11.414 10l4.293 4.293a1 1 0 01-1.414 1.414L10 11.414l-4.293 4.293a1 1 0 01-1.414-1.414L8.586 10 4.293 5.707a1 1 0 010-1.414z" clip-rule="evenodd"></path></svg></button>
                        </div>
                    </div>`;
                }}
            }});
            }})();
        </script>
    """,
    )


def dark_mode_expr(dark_mode: str) -> str:
    """Build the Alpine expression resolving the initial dark-mode state."""
    if dark_mode == "dark":
        server_default_expr = "true"
    elif dark_mode == "light":
        server_default_expr = "false"
    else:
        server_default_expr = "(window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches)"
    return (
        "localStorage.getItem('darkMode') !== null ? "
        "localStorage.getItem('darkMode') === 'true' : "
        f"{server_default_expr}"
    )

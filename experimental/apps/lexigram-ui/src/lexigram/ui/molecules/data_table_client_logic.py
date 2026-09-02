from __future__ import annotations

from typing import Any

from lexigram.ui import Zones, el, js_json, raw


class DataTableScriptRenderer:
    """Renderer for the client-side Alpine.js logic of the DataTable."""

    @staticmethod
    def render(all_ids: list[str]) -> Any:
        # We assume all_ids is already a list of strings
        script_js = f"""
        (function() {{
            // Keep downloads as native form submissions. HTMX receives CSV
            // bytes through XHR and cannot turn Content-Disposition into a
            // browser download, while a temporary form preserves cookies,
            // CSRF fields, and the selected IDs.
            window.LexigramDownloadBulk = window.LexigramDownloadBulk || function(button) {{
                const table = document.querySelector('{Zones.TABLE.selector}');
                const checked = table ? table.querySelectorAll('input[name="ids"]:checked') : [];
                const filtered = !checked.length;

                const form = document.createElement('form');
                form.method = 'post';
                form.action = button.dataset.bulkDownloadUrl || '';
                form.target = '_blank';
                form.style.display = 'none';

                const add = (name, value) => {{
                    const input = document.createElement('input');
                    input.type = 'hidden';
                    input.name = name;
                    input.value = value;
                    form.appendChild(input);
                }};
                add('action', button.dataset.bulkAction || 'export');
                if (filtered) {{
                    // R25: no selection means "export everything matching
                    // the current view" — forward the list's URL state.
                    add('scope', 'filtered');
                    add('list_query', window.location.search.replace(/^\\?/, ''));
                }} else {{
                    checked.forEach((checkbox) => add('ids', checkbox.value));
                }}
                const csrf = table && table.querySelector('input[name="csrf_token"]');
                if (csrf) add('csrf_token', csrf.value);

                document.body.appendChild(form);
                form.submit();
                form.remove();
                return false;
            }};

            // Import uploads (B31): the Import header action button carries
            // data-import-upload-url / data-import-accept. Open a file
            // picker, then POST the file with the CSRF token. fetch (not a
            // native form) so the JSON/HTML fragment response can surface a
            // toast instead of navigating away from the list.
            window.LexigramImportUpload = window.LexigramImportUpload || function(button) {{
                const url = button.dataset.importUploadUrl || '';
                if (!url) return false;
                const notify = function(message, type) {{
                    if (window.showToast) window.showToast(message, type);
                    else if (window.alert) window.alert(message);
                }};
                const picker = document.createElement('input');
                picker.type = 'file';
                picker.accept = button.dataset.importAccept || '.csv,.json,.jsonl';
                picker.style.display = 'none';
                picker.addEventListener('change', async function() {{
                    const file = picker.files && picker.files[0];
                    picker.remove();
                    if (!file) return;
                    try {{
                        const body = new FormData();
                        body.append('file', file, file.name);
                        const table = document.querySelector('{Zones.TABLE.selector}');
                        const csrfInput = table && table.querySelector('input[name="csrf_token"]');
                        const csrfEl = document.querySelector('[data-csrf-token]');
                        const csrf = (csrfInput && csrfInput.value) ||
                            window.__lexigramCsrfToken ||
                            (csrfEl && csrfEl.getAttribute('data-csrf-token'));
                        const headers = {{ 'HX-Request': 'true' }};
                        if (csrf) {{
                            headers['X-CSRF-Token'] = csrf;
                            body.append('csrf_token', csrf);
                        }}
                        const response = await fetch(url, {{
                            method: 'POST',
                            body: body,
                            headers: headers,
                            credentials: 'same-origin'
                        }});
                        const text = await response.text();
                        if (!response.ok) {{
                            const detail = text.replace(/<[^>]*>/g, ' ').trim().slice(0, 200);
                            notify('Import failed: ' + (detail || response.status), 'error');
                            return;
                        }}
                        notify('Import finished. Reloading…', 'success');
                        setTimeout(function() {{ window.location.reload(); }}, 600);
                    }} catch (err) {{
                        notify('Import failed.', 'error');
                    }}
                }});
                document.body.appendChild(picker);
                picker.click();
                return false;
            }};

            if (window.LexigramTableInitialized) return;
            window.LexigramTableInitialized = true;

            window.LexigramTableLogic = {{
                allIds: {js_json(all_ids)},
                hasActiveFiltersState: false,

                updateActiveFiltersState() {{
                    const searchInput = document.getElementById('{Zones.SEARCH.id}-input');
                    const hasSearch = searchInput && searchInput.value && searchInput.value.trim() !== '';
                    const filterBar = document.getElementById('{Zones.FILTERS.id}');
                    let hasFilters = false;
                    if (filterBar) {{
                        // Consider filters active only if any control has a non-empty/checked value
                        const controls = Array.from(filterBar.querySelectorAll('select, input, textarea'));
                        for (const ctrl of controls) {{
                            if (!ctrl) continue;
                            const tag = (ctrl.tagName || '').toUpperCase();
                            const type = (ctrl.type || '').toLowerCase();
                            if (tag === 'SELECT') {{
                                if (ctrl.value !== '' && ctrl.value !== null) {{ hasFilters = true; break; }}
                            }} else if (type === 'checkbox' || type === 'radio') {{
                                if (ctrl.checked) {{ hasFilters = true; break; }}
                            }} else {{
                                if (ctrl.value && String(ctrl.value).trim() !== '') {{ hasFilters = true; break; }}
                            }}
                        }}
                    }}
                    this.hasActiveFiltersState = hasSearch || hasFilters;
                }},


                toggleSelect(id) {{
                    id = String(id);
                    if (this.selectedIds.includes(id)) {{
                        this.selectedIds = this.selectedIds.filter(i => i != id);
                    }} else {{
                        this.selectedIds.push(id);
                    }}
                    this.lastSelected = id;
                }},

                handleSelect(id, event) {{
                    id = String(id);
                    if (event.shiftKey && this.lastSelected) {{
                        const start = this.allIds.indexOf(this.lastSelected);
                        const end = this.allIds.indexOf(id);
                        if (start !== -1 && end !== -1) {{
                            const range = this.allIds.slice(Math.min(start, end), Math.max(start, end) + 1);
                            this.selectedIds = [...new Set([...this.selectedIds, ...range])];
                        }}
                    }} else {{
                        if (this.selectedIds.includes(id)) {{
                            this.selectedIds = this.selectedIds.filter(i => i != id);
                        }} else {{
                            this.selectedIds = [...this.selectedIds, id];
                        }}
                    }}
                    this.lastSelected = id;
                    this.focusedId = id;
                }},

                toggleExpand(id) {{
                    id = String(id);
                    if (this.expandedIds.includes(id)) {{
                        this.expandedIds = this.expandedIds.filter(i => i != id);
                    }} else {{
                        this.expandedIds.push(id);
                    }}
                }},

                nextRow() {{
                    if (!this.allIds.length) return;
                    const idx = this.focusedId ? this.allIds.indexOf(this.focusedId) : -1;
                    const next = idx + 1 < this.allIds.length ? this.allIds[idx + 1] : this.allIds[0];
                    this.focusedId = next;
                }},

                prevRow() {{
                    if (!this.allIds.length) return;
                    const idx = this.focusedId ? this.allIds.indexOf(this.focusedId) : -1;
                    const prev = idx - 1 >= 0 ? this.allIds[idx - 1] : this.allIds[this.allIds.length - 1];
                    this.focusedId = prev;
                }},

                selectAll() {{
                    this.selectedIds = [...this.allIds];
                }},

                handleSelectAll(event) {{
                    if (event.target.checked) {{
                        this.selectedIds = [...this.allIds];
                    }} else {{
                        this.selectedIds = [];
                    }}
                }},

                refreshAllIds(newIds) {{
                    this.allIds = newIds.map(id => String(id));
                    this.selectedIds = this.selectedIds.filter(id => this.allIds.includes(id));
                    this.lastSelected = null;
                }},

                reorderColumn(fromCol, toCol) {{
                    if (fromCol === toCol) return;

                    // Get current column names from the headers
                    const ths = Array.from(document.querySelectorAll('{Zones.TABLE.selector} thead th[data-col-name]'));
                    let colNames = ths.map(th => th.getAttribute('data-col-name'));

                    if (colNames.length === 0) {{
                        // Fallback if data-col-name is missing (should not happen with my update)
                        return;
                    }}

                    const fromIdx = colNames.indexOf(fromCol);
                    const toIdx = colNames.indexOf(toCol);

                    if (fromIdx !== -1 && toIdx !== -1) {{
                        colNames.splice(toIdx, 0, colNames.splice(fromIdx, 1)[0]);

                        // Update the hidden input
                        const input = document.querySelector('input[name="col_order"]');
                        if (input) {{
                            input.value = colNames.join(',');
                            // Trigger HTMX refresh by submitting the form or triggering a change
                            input.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        }}
                    }}
                }},

                toggleGroup(groupName) {{
                    groupName = String(groupName);
                    if (this.collapsedGroups.includes(groupName)) {{
                        this.collapsedGroups = this.collapsedGroups.filter(g => g !== groupName);
                    }} else {{
                        this.collapsedGroups.push(groupName);
                    }}

                    // Keep in sync with hidden input for server state persistence on next load
                    const input = document.querySelector('input[name="collapsed_groups"]');
                    if (input) {{
                        input.value = this.collapsedGroups.join(',');
                    }}
                }},

                handleKeydown(e) {{
                     if (['INPUT', 'TEXTAREA'].includes(e.target.tagName)) {{
                         if (e.key === 'Escape') e.target.blur();
                         return;
                     }}

                     switch(e.key) {{
                          case 'ArrowDown':
                              e.preventDefault();
                              this.nextRow();
                              break;
                          case 'ArrowUp':
                              e.preventDefault();
                              this.prevRow();
                              break;
                          case 'a':
                              if (e.metaKey || e.ctrlKey) {{
                                  e.preventDefault();
                                  this.selectAll();
                              }}
                              break;
                          case ' ':
                              if (e.target.tagName !== 'BUTTON') {{
                                  e.preventDefault();
                                  if (this.focusedId) this.toggleSelect(this.focusedId);
                              }}
                              break;
                          case '/':
                              e.preventDefault();
                              document.getElementById('{Zones.SEARCH.id}')?.focus();
                              break;
                     }}
                }}
            }};

            // Register resizable columns robustly
            const registerResizable = () => {{
                if (window.Alpine && !window.LexigramResizableRegistered) {{
                    Alpine.data('resizableColumn', () => ({{
                        startResize(e) {{
                             const th = this.$el;
                             const startX = e.clientX;
                             const startWidth = th.offsetWidth;
                             const onMove = (moveEvent) => {{
                                 const currentWidth = startWidth + (moveEvent.clientX - startX);
                                 if (currentWidth > 50) {{
                                     th.style.width = `${{currentWidth}}px`;
                                     th.style.minWidth = `${{currentWidth}}px`;
                                 }}
                             }};
                             const onUp = () => {{
                                 window.removeEventListener('mousemove', onMove);
                                 window.removeEventListener('mouseup', onUp);
                             }};
                             window.addEventListener('mousemove', onMove);
                             window.addEventListener('mouseup', onUp);
                        }}
                    }}));
                    window.LexigramResizableRegistered = true;
                }}
            }};

            if (window.Alpine) {{
                registerResizable();
            }} else {{
                document.addEventListener('alpine:init', registerResizable);
            }}

            document.addEventListener('htmx:afterSwap', (e) => {{
                try {{
                    const target = e.detail.target;
                    if (window.htmx && target) {{
                        try {{ htmx.process(target); }} catch (err) {{ }}
                    }}
                    if (window.LexigramTableLogic && typeof window.LexigramTableLogic.updateActiveFiltersState === 'function') {{
                        window.LexigramTableLogic.updateActiveFiltersState();
                    }}
                    if (target && target.id === '{Zones.DATA.id}') {{
                        const checkboxes = target.querySelectorAll('input[name="ids"]');
                        const newIds = Array.from(checkboxes).map(cb => cb.value);
                        const tableEl = document.getElementById('{Zones.TABLE.id}');
                        if (tableEl && window.Alpine) {{
                            Alpine.$data(tableEl).refreshAllIds(newIds);
                        }}
                    }}
                }} catch (err) {{ }}
            }});

            document.addEventListener('htmx:beforeSwap', (e) => {{
                try {{
                    const targetId = e.detail.target?.id;
                    if (targetId !== '{Zones.TABLE.id}' && targetId !== 'main-content') return;
                    const fragment = e.detail.serverResponse;
                    if (!fragment) return;
                    const doc = new DOMParser().parseFromString(fragment, 'text/html');
                    const newInput = doc.querySelector('#{Zones.SEARCH.id}-input');
                    const oldInput = document.getElementById('{Zones.SEARCH.id}-input');
                    if (!newInput || !oldInput) return;
                    ['hx-get','hx-trigger','hx-target','hx-swap','hx-include','hx-vals','hx-push-url','placeholder'].forEach(attr => {{
                        const val = newInput.getAttribute(attr);
                        if (val != null) oldInput.setAttribute(attr, val);
                    }});
                }} catch (err) {{ }}
            }});

            function updateSidebarActive(url) {{
                const sidebarLinks = document.querySelectorAll('#main-sidebar nav a[hx-get]');
                sidebarLinks.forEach(link => {{
                    const href = link.getAttribute('hx-get');
                    const isActive = url === href || url.startsWith(href + '/');
                    const activeCls = 'bg-primary-50 dark:bg-primary-900/20 text-primary-700 dark:text-primary-400';
                    const inactiveCls = 'text-muted-foreground dark:text-muted-foreground hover:bg-muted dark:hover:bg-card/50 hover:text-primary-600 dark:hover:text-primary-400';
                    if (isActive) {{
                        link.classList.remove(...inactiveCls.split(' ').filter(c => c));
                        link.classList.add(...activeCls.split(' ').filter(c => c));
                        link.setAttribute('aria-current', 'page');
                    }} else {{
                        link.classList.remove(...activeCls.split(' ').filter(c => c));
                        link.classList.add(...inactiveCls.split(' ').filter(c => c));
                        link.setAttribute('aria-current', 'false');
                    }}
                }});
            }}

            document.addEventListener('htmx:afterSettle', (e) => {{
                try {{
                    const targetId = e.detail.target?.id;
                    if (targetId === 'main-content' || targetId === '{Zones.TABLE.id}') {{
                        updateSidebarActive(window.location.pathname);
                    }}
                }} catch (err) {{ }}
            }});
        }})();
        """
        return el("script", raw(script_js))

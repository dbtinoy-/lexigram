from __future__ import annotations

from typing import Any

from lexigram.serialization import dumps_str
from lexigram.ui import Zones, el


class DataTableScriptRenderer:
    """Renderer for the client-side Alpine.js logic of the DataTable."""

    @staticmethod
    def render(all_ids: list[str]) -> Any:
        # We assume all_ids is already a list of strings
        script_js = f"""
        (function() {{
            if (window.LexigramTableInitialized) return;
            window.LexigramTableInitialized = true;

            window.LexigramTableLogic = {{
                allIds: {dumps_str(all_ids)},
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
                    if (window.Alpine && target) {{
                        try {{ Alpine.initTree(target); }} catch (err) {{ }}
                    }}
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
        return el("script", script_js)

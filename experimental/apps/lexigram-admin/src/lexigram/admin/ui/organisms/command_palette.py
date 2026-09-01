from __future__ import annotations

from typing import Any

from lexigram.serialization import dumps_str
from lexigram.ui import Component, el, raw


class CommandPalette(Component):
    """
    A global command palette (Cmd+K) for quick navigation and actions.
    Powered by Alpine.js for state and keyboard handling.
    """

    def __init__(
        self,
        commands: list[dict[str, str]] | None = None,
        admin_prefix: str = "/admin",
        **props,
    ) -> None:
        super().__init__(commands=commands or [], **props)
        self.admin_prefix = admin_prefix.rstrip("/") or "/admin"
        self.commands = commands or [
            {
                "label": "Go to Dashboard",
                "href": f"{self.admin_prefix}/",
                "icon": "home",
                "shortcut": "G D",
            },
            {
                "label": "Manage Users",
                "href": f"{self.admin_prefix}/users/",
                "icon": "users",
                "shortcut": "G U",
            },
            {
                "label": "Toggle Dark Mode",
                "action": "darkMode = !darkMode",
                "icon": "moon",
                "shortcut": "T D",
            },
            {
                "label": "Settings",
                "href": f"{self.admin_prefix}/settings",
                "icon": "settings",
                "shortcut": ",",
            },
        ]

    def render(self) -> Any:
        from lexigram.ui import get_icon

        # Pre-process commands to include rendered icon HTML
        processed_commands = []
        for cmd in self.commands:
            c = cmd.copy()
            # Render icon to string
            icon_node = get_icon(
                c.get("icon", ""),
                class_name="w-6 h-6 text-muted-foreground group-hover:text-foreground transition-colors",
            )
            c["icon_html"] = str(icon_node)
            processed_commands.append(c)

        command_palette_url = f"{self.admin_prefix}/command-palette"
        # JSON is embedded in a script element. Escape HTML-significant
        # characters so a contributor-supplied command label cannot terminate
        # the script block before Alpine parses the data.
        commands_json = (
            dumps_str(processed_commands)
            .replace("<", "\\u003c")
            .replace(">", "\\u003e")
            .replace("&", "\\u0026")
        )

        # Alpine.js state for the palette (kept for reference)
        _x_data = {
            "open": False,
            "search": "",
            "searchTimeout": None,
            "selectedIndex": 0,
            "commands": processed_commands,
            "staticCommands": processed_commands,
        }

        # Overlay and Modal structure
        return el(
            "div",
            {
                "x-data": "commandPalette",
                "x-on:open-command-palette.window": "toggle()",
                "x-on:keydown.window.cmd.k.prevent": "toggle()",
                "x-on:keydown.window.ctrl.k.prevent": "toggle()",
                "x-on:keydown.window.escape": "close()",
                "x-show": "open",
                "class": "fixed inset-0 z-50 overflow-y-auto p-4 sm:p-6 md:p-20",
                "role": "dialog",
                "aria-modal": "true",
                "aria-label": "Command palette",
                # Trap focus inside the palette while open (Alpine Focus
                # plugin — vendored as alpine-focus.min.js in the shell).
                "x-trap.noscroll": "open",
                "x-cloak": True,
            },
            # Backdrop
            el(
                "div",
                {
                    "x-show": "open",
                    "x-transition:enter": "transition-opacity ease-out duration-300",
                    "x-transition:enter-start": "opacity-0",
                    "x-transition:enter-end": "opacity-100",
                    "x-transition:leave": "transition-opacity ease-in duration-200",
                    "x-transition:leave-start": "opacity-100",
                    "x-transition:leave-end": "opacity-0",
                    "class": "fixed inset-0 bg-muted/60 backdrop-blur-sm transition-opacity",
                    "x-on:click": "close()",
                },
            ),
            # Palette Container
            el(
                "div",
                {
                    "x-show": "open",
                    "x-transition:enter": "transition-all ease-out duration-300",
                    "x-transition:enter-start": "opacity-0 scale-95",
                    "x-transition:enter-end": "opacity-100 scale-100",
                    "x-transition:leave": "transition-all ease-in duration-200",
                    "x-transition:leave-start": "opacity-100 scale-100",
                    "x-transition:leave-end": "opacity-0 scale-95",
                    "class": "mx-auto max-w-2xl transform divide-y divide-border overflow-hidden rounded-2xl bg-background shadow-2xl ring-1 ring-border transition-all",
                },
                # Search Input
                el(
                    "div",
                    el(
                        "div",
                        get_icon("search", class_name="h-5 w-5 text-muted-foreground"),
                        class_="pointer-events-none absolute left-4 top-3.5 h-5 w-5",
                    ),
                    el(
                        "input",
                        {
                            "type": "text",
                            "class": "h-12 w-full border-0 bg-transparent pl-11 pr-4 text-foreground placeholder:text-muted-foreground focus:ring-0 sm:text-sm",
                            "placeholder": "Search commands or navigation...",
                            # Combobox pattern: the input drives the listbox
                            # below and exposes the active option to AT.
                            "role": "combobox",
                            "aria-expanded": "true",
                            "aria-controls": "command-palette-options",
                            "aria-autocomplete": "list",
                            "aria-label": "Search commands and navigation",
                            ":aria-activedescendant": "'command-palette-option-' + selectedIndex",
                            "x-model": "search",
                            # B13: kwarg underscores render dead `x-on-*`
                            # attributes — Alpine needs the canonical form.
                            "x-on:keydown.down.prevent": "next()",
                            "x-on:keydown.up.prevent": "prev()",
                            "x-on:keydown.enter.prevent": "execute()",
                        },
                    ),
                    class_="relative",
                ),
                # Results list
                el(
                    "ul",
                    {
                        "class": "max-h-96 scroll-py-3 overflow-y-auto p-3",
                        "id": "command-palette-options",
                        "role": "listbox",
                        "aria-label": "Commands",
                    },
                    el(
                        "template",
                        {
                            "x-for": "(command, index) in filteredCommands",
                            ":key": "command.label",
                        },
                        el(
                            "li",
                            {
                                "class": "group flex cursor-default select-none items-center rounded-xl p-3",
                                ":class": "selectedIndex === index ? 'bg-primary-600 text-white' : 'text-foreground hover:bg-muted dark:hover:bg-card'",
                                ":id": "'command-palette-option-' + index",
                                ":aria-selected": "selectedIndex === index ? 'true' : 'false'",
                                "role": "option",
                                "tabindex": "-1",
                                # B13: `x_on_*` rendered dead `x-on-*` attrs —
                                # option click/hover never worked before.
                                "x-on:click": "execute(index)",
                                "x-on:mouseenter": "selectedIndex = index",
                            },
                            # Icon
                            el(
                                "div",
                                {
                                    "class": "flex h-10 w-10 flex-none items-center justify-center rounded-lg",
                                    ":class": "selectedIndex === index ? 'bg-primary-500' : 'bg-muted dark:bg-card'",
                                },
                                el(
                                    "div",
                                    {
                                        "x-html": "command.icon_html",
                                        "class": "flex items-center justify-center",
                                    },
                                ),
                            ),
                            # Label
                            el(
                                "div",
                                el(
                                    "p",
                                    {
                                        "x-text": "command.label",
                                        "class": "font-semibold",
                                    },
                                ),
                                class_="ml-4 flex-auto",
                            ),
                            # Shortcut
                            el(
                                "span",
                                {
                                    "x-show": "command.shortcut",
                                    "x-text": "command.shortcut",
                                    "class": "ml-3 flex-none text-xs font-semibold",
                                    ":class": "selectedIndex === index ? 'text-primary-100' : 'text-muted-foreground'",
                                },
                            ),
                        ),
                    ),
                ),
                # Empty state
                el(
                    "div",
                    el(
                        "p",
                        "No results found for that search.",
                        class_="p-10 text-center text-sm text-muted-foreground",
                    ),
                    x_show="search !== '' && filteredCommands.length === 0",
                ),
                # Help footer
                el(
                    "div",
                    el(
                        "div",
                        el(
                            "span",
                            "esc",
                            class_="rounded-md border border-border px-1.5 py-0.5 text-xs font-semibold text-muted-foreground",
                        ),
                        el(
                            "span",
                            " to close",
                            class_="ml-1 text-xs text-muted-foreground",
                        ),
                        class_="flex items-center",
                    ),
                    el(
                        "div",
                        el(
                            "span",
                            "enter",
                            class_="rounded-md border border-border px-1.5 py-0.5 text-xs font-semibold text-muted-foreground",
                        ),
                        el(
                            "span",
                            " to select",
                            class_="ml-1 text-xs text-muted-foreground",
                        ),
                        class_="flex items-center ml-4",
                    ),
                    class_="flex flex-none items-center justify-end bg-muted dark:bg-card/50 px-4 py-2.5",
                ),
            ),
            # Inline script to register Alpine data
            el(
                "script",
                raw(
                    f"""
                document.addEventListener('alpine:init', () => {{
                    Alpine.data('commandPalette', () => ({{
                        open: false,
                        search: '',
                        selectedIndex: 0,
                        searchTimeout: null,
                        commands: {commands_json},
                        staticCommands: {commands_json},
                        get filteredCommands() {{
                            return this.commands;
                        }},
                        init() {{
                            this.$watch('search', (value) => {{
                                clearTimeout(this.searchTimeout);
                                this.selectedIndex = 0;
                                this.searchTimeout = setTimeout(() => {{
                                    this.fetchResults(value);
                                }}, 200);
                            }});
                        }},
                        async fetchResults(query) {{
                            if (query.length < 2) {{
                                this.commands = this.staticCommands;
                                return;
                            }}
                            try {{
                                const response = await fetch(`{command_palette_url}?q=${{encodeURIComponent(query)}}`);
                                const data = await response.json();
                                this.commands = data;
                            }} catch (e) {{
                                this.commands = this.staticCommands;
                            }}
                        }},
                        toggle() {{
                            this.open = !this.open;
                            if (this.open) {{
                                this.search = '';
                                this.selectedIndex = 0;
                                setTimeout(() => this.$el.querySelector('input').focus(), 50);
                            }}
                        }},
                        close() {{
                            this.open = false;
                        }},
                        next() {{
                            this.selectedIndex = (this.selectedIndex + 1) % this.filteredCommands.length;
                        }},
                        prev() {{
                            this.selectedIndex = (this.selectedIndex - 1 + this.filteredCommands.length) % this.filteredCommands.length;
                        }},
                        execute(idx = null) {{
                            const index = idx !== null ? idx : this.selectedIndex;
                            const command = this.filteredCommands[index];
                            if (!command) return;

                            this.close();

                            if (command.href) {{
                                if (command.href.startsWith('/')) {{
                                    // Use htmx if possible
                                    if (window.htmx) {{
                                        htmx.ajax('GET', command.href, {{target:'#main-content', swap:'innerHTML'}})
                                        window.history.pushState({{}}, '', command.href);
                                    }} else {{
                                        window.location.href = command.href;
                                    }}
                                }} else {{
                                    window.location.href = command.href;
                                }}
                            }} else if (command.action) {{
                                // Find the shell's x-data to execute actions
                                const shell = document.querySelector('[x-data*="darkMode"]');
                                if (shell) {{
                                    const data = Alpine.$data(shell);
                                    if (command.action.includes('darkMode')) {{
                                        data.darkMode = !data.darkMode;
                                    }}
                                }}
                            }}
                        }}
                    }}))
                }})
            """,
                ),
            ),
        )

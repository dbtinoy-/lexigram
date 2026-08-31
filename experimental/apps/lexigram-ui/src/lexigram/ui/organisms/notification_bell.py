from __future__ import annotations

from typing import Any

from lexigram.ui import Component, el, raw
from lexigram.ui.atoms.icons import get_icon
from lexigram.ui.core.js import js_string


class NotificationBell(Component):
    """In-app notification bell with real-time updates via SSE.

    Alpine.js-driven component that loads the persisted inbox from the
    admin JSON endpoints, displays an unread count badge on the bell
    icon, and shows a dropdown of recent notifications with
    mark-as-read support (posting back to the inbox endpoints).

    Args:
        sse_url: SSE endpoint URL for real-time notification events.
        inbox_url: Link to the full notification inbox page. The
            "View all" footer is only rendered when a URL is set.
        inbox_api_url: JSON endpoint returning the persisted inbox
            (``{"unread_count": ..., "notifications": [...]}``).
        mark_read_url: POST endpoint marking one message read; the
            literal ``{message_id}`` placeholder is replaced with the
            message ID.
        mark_all_read_url: POST endpoint marking every message read.
        csrf_token: Token sent with notification mutation requests.
        max_display: Maximum number of notifications shown in the dropdown.
        **props: Extra HTML attributes forwarded to the root element.
    """

    def __init__(
        self,
        sse_url: str = "/admin/_sse/widgets",
        inbox_url: str | None = None,
        inbox_api_url: str = "/admin/notifications/inbox",
        mark_read_url: str = "/admin/notifications/read/{message_id}",
        mark_all_read_url: str = "/admin/notifications/read-all",
        csrf_token: str | None = None,
        max_display: int = 10,
        **props: Any,
    ) -> None:
        super().__init__(**props)
        self.sse_url = sse_url
        self.inbox_url = inbox_url
        self.inbox_api_url = inbox_api_url
        self.mark_read_url = mark_read_url
        self.mark_all_read_url = mark_all_read_url
        self.csrf_token = csrf_token or ""
        self.max_display = max_display

    def render(self) -> Any:
        bell_icon = get_icon("bell", class_name="w-5 h-5")

        return el(
            "div",
            {
                "x-data": "notificationBell",
                "x-init": "init()",
                "x-on:beforeunload.window": "destroy()",
                "data-inbox-url": self.inbox_url or "",
                "data-inbox-api-url": self.inbox_api_url,
                "data-sse-url": self.sse_url,
                "data-csrf-token": self.csrf_token,
                "class": "relative",
            },
            # Bell button
            el(
                "button",
                {
                    "type": "button",
                    "x-on:click": "toggle()",
                    "class": "relative p-2 rounded-lg hover:bg-muted dark:hover:bg-card transition-colors focus:outline-none focus:ring-2 focus:ring-primary-500",
                    "aria-label": "Notifications",
                },
                bell_icon,
                el(
                    "span",
                    {
                        "x-show": "unreadCount > 0",
                        "x-text": "unreadCount > 99 ? '99+' : unreadCount",
                        "class": "absolute -top-0.5 -right-0.5 inline-flex items-center justify-center px-1.5 py-0.5 text-[10px] font-bold leading-none text-white bg-destructive rounded-full min-w-[16px]",
                    },
                ),
            ),
            # Dropdown
            el(
                "div",
                {
                    "x-show": "open",
                    "x-cloak": True,
                    "x-on:click.away": "close()",
                    "x-transition:enter": "transition ease-out duration-200",
                    "x-transition:enter-start": "opacity-0 translate-y-1",
                    "x-transition:enter-end": "opacity-100 translate-y-0",
                    "x-transition:leave": "transition ease-in duration-150",
                    "x-transition:leave-start": "opacity-100 translate-y-0",
                    "x-transition:leave-end": "opacity-0 translate-y-1",
                    "class": "absolute right-0 mt-2 w-80 rounded-xl shadow-lg bg-card ring-1 ring-border divide-y divide-border z-50",
                },
                # Header
                el(
                    "div",
                    {"class": "flex items-center justify-between px-4 py-3"},
                    el(
                        "h3",
                        {"class": "text-sm font-semibold text-foreground"},
                        "Notifications",
                    ),
                    el(
                        "button",
                        {
                            "x-on:click": "markAllRead()",
                            "x-show": "unreadCount > 0",
                            "class": "text-xs text-primary-600 dark:text-primary-400 hover:underline",
                        },
                        "Mark all read",
                    ),
                ),
                # Notification list
                el(
                    "div",
                    {"class": "max-h-64 overflow-y-auto"},
                    el(
                        "template",
                        {"x-for": "(notif, idx) in notifications", ":key": "notif.id"},
                        el(
                            "div",
                            {
                                ":class": "notif.read ? 'opacity-60' : ''",
                                "class": "flex items-start gap-3 px-4 py-3 hover:bg-muted dark:hover:bg-muted/50 cursor-pointer transition-colors",
                                "x-on:click": "markAsRead(notif.id)",
                            },
                            # Level indicator dot
                            el(
                                "span",
                                {
                                    "class": "mt-1.5 w-2 h-2 rounded-full flex-shrink-0",
                                    ":class": "{'bg-info': notif.level === 'info', 'bg-warning': notif.level === 'warning', 'bg-destructive': notif.level === 'error', 'bg-success': notif.level === 'success'}",
                                },
                            ),
                            # Content
                            el(
                                "div",
                                el(
                                    "p",
                                    {
                                        "x-text": "notif.title",
                                        "class": "text-sm font-medium text-foreground",
                                    },
                                ),
                                el(
                                    "p",
                                    {
                                        "x-text": "notif.message",
                                        "class": "text-xs text-muted-foreground dark:text-muted-foreground mt-0.5 line-clamp-2",
                                    },
                                ),
                                class_="flex-1 min-w-0",
                            ),
                        ),
                    ),
                    # Empty state
                    el(
                        "div",
                        {
                            "x-show": "notifications.length === 0",
                            "class": "px-4 py-8 text-center text-sm text-muted-foreground dark:text-muted-foreground",
                        },
                        "No new notifications",
                    ),
                ),
                # Footer (only when an inbox page exists)
                *(
                    (
                        el(
                            "div",
                            el(
                                "a",
                                {
                                    "href": self.inbox_url,
                                    "class": "block w-full text-center px-4 py-2 text-xs text-primary-600 dark:text-primary-400 hover:bg-muted dark:hover:bg-muted/50 rounded-b-xl transition-colors",
                                },
                                "View all notifications",
                            ),
                        ),
                    )
                    if self.inbox_url
                    else ()
                ),
            ),
            # Alpine.js component registration
            el(
                "script",
                raw(f"""
document.addEventListener('alpine:init', () => {{
    Alpine.data('notificationBell', () => ({{
        open: false,
        unreadCount: 0,
        notifications: [],
        eventSource: null,
        toggle() {{ this.open = !this.open; }},
        close() {{ this.open = false; }},
        init() {{
            this.loadInbox();
            if (this.eventSource) return;
            this.eventSource = new EventSource({js_string(self.sse_url)});
            const handleNotification = (e) => {{
                const envelope = JSON.parse(e.data);
                // The widget SSE bridge sends AdminEvent.to_dict() as the
                // default message payload, while direct SSE implementations
                // may set the event field to `notification` and send the
                // inner data object. Support both wire shapes.
                if (envelope.event && envelope.event !== 'notification') return;
                const data = envelope.data || envelope;
                this.notifications.unshift({{
                    id: envelope.id || data.id || Date.now() + Math.random(),
                    title: data.title || 'Notification',
                    message: data.message || '',
                    level: data.level || 'info',
                    read: false,
                    time: data.timestamp
                }});
                this.unreadCount++;
                if (this.notifications.length > {int(self.max_display)}) {{
                    this.notifications.pop();
                }}
            }};
            this.eventSource.addEventListener('message', handleNotification);
            this.eventSource.addEventListener('notification', handleNotification);
            this.eventSource.addEventListener('toast', (e) => {{
                const data = JSON.parse(e.data);
                if (typeof window.showToast === 'function') {{
                    window.showToast(data.message || data.title, data.variant || 'success');
                }}
            }});
            this.eventSource.addEventListener('error', () => {{}});
            const el = this.$el;
            const observer = new MutationObserver(() => {{
                if (!el.isConnected) {{
                    observer.disconnect();
                    this.destroy();
                }}
            }});
            observer.observe(document.body, {{ childList: true, subtree: true }});
            this._observer = observer;
        }},
        async loadInbox() {{
            try {{
                const res = await fetch({js_string(self.inbox_api_url)}, {{
                    headers: {{'X-Requested-With': 'fetch'}}
                }});
                if (!res.ok) return;
                const data = await res.json();
                this.notifications = (data.notifications || []).map(n => ({{
                    id: n.id,
                    title: n.title || 'Notification',
                    message: n.message || '',
                    level: n.level || 'info',
                    read: n.read === true,
                    time: n.timestamp
                }}));
                this.unreadCount = data.unread_count || 0;
            }} catch (e) {{}}
        }},
        destroy() {{
            if (this._observer) {{
                this._observer.disconnect();
                this._observer = null;
            }}
            if (this.eventSource) this.eventSource.close();
        }},
        async markAsRead(id) {{
            const notif = this.notifications.find(n => n.id === id);
            if (notif && !notif.read) {{
                notif.read = true;
                this.unreadCount = Math.max(0, this.unreadCount - 1);
            }}
            try {{
                await fetch({js_string(self.mark_read_url)}.replace('{{message_id}}', id), {{
                    method: 'POST',
                    headers: {{
                        'X-Requested-With': 'fetch',
                        'X-CSRF-Token': this.$el.dataset.csrfToken || ''
                    }}
                }});
            }} catch (e) {{}}
        }},
        async markAllRead() {{
            this.notifications.forEach(n => n.read = true);
            this.unreadCount = 0;
            try {{
                await fetch({js_string(self.mark_all_read_url)}, {{
                    method: 'POST',
                    headers: {{
                        'X-Requested-With': 'fetch',
                        'X-CSRF-Token': this.$el.dataset.csrfToken || ''
                    }}
                }});
            }} catch (e) {{}}
        }}
    }}));
}});
"""),
            ),
        )

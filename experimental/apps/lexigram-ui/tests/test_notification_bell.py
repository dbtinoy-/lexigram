"""Render tests for the NotificationBell Alpine component."""

from __future__ import annotations


def test_bell_renders_badge_and_alpine_root() -> None:
    """Bell should be an Alpine component with an unread count badge."""
    from lexigram.ui import NotificationBell

    bell = NotificationBell()
    html = str(bell)

    assert 'x-data="notificationBell"' in html
    assert "x-init" in html
    assert "unreadCount &gt; 0" in html
    assert "99+" in html
    assert 'aria-label="Notifications"' in html


def test_bell_renders_notification_list_and_empty_state() -> None:
    """Dropdown should iterate notifications and show an empty state."""
    from lexigram.ui import NotificationBell

    html = str(NotificationBell())

    assert "x-for" in html
    assert "notif.title" in html
    assert "notif.message" in html
    assert "notifications.length === 0" in html
    assert "No new notifications" in html


def test_bell_wires_mark_read_handlers() -> None:
    """Bell should render mark-as-read and mark-all-read handlers."""
    from lexigram.ui import NotificationBell

    html = str(NotificationBell())

    assert "markAsRead" in html
    assert "markAllRead" in html
    assert "Mark all read" in html
    assert "unreadCount = Math.max(0, this.unreadCount - 1)" in html


def test_bell_connects_to_sse_endpoint() -> None:
    """Bell should open an EventSource to the configured SSE URL."""
    from lexigram.ui import NotificationBell

    bell = NotificationBell(sse_url="/custom/events")
    html = str(bell)

    # URLs are emitted as encoded JS literals (double-quoted by js_string),
    # not hand-quoted, so that a URL cannot break out of the script.
    assert 'new EventSource("/custom/events")' in html
    assert "addEventListener('message'" in html
    assert "addEventListener('notification'" in html
    assert "addEventListener('toast'" in html


def test_bell_loads_persisted_inbox() -> None:
    """Bell should fetch the persisted inbox on init."""
    from lexigram.ui import NotificationBell

    html = str(NotificationBell())

    assert "loadInbox()" in html
    assert 'fetch("/admin/notifications/inbox"' in html
    assert "'X-Requested-With': 'fetch'" in html
    assert "data.unread_count" in html
    assert "data.notifications" in html


def test_bell_posts_mark_read_to_inbox_endpoints() -> None:
    """Bell should POST mark-read and mark-all-read to the endpoints."""
    from lexigram.ui import NotificationBell

    bell = NotificationBell(
        mark_read_url="/custom/read/{message_id}",
        mark_all_read_url="/custom/read-all",
    )
    html = str(bell)

    assert 'fetch("/custom/read/{message_id}".replace' in html
    assert "method: 'POST'" in html
    assert 'fetch("/custom/read-all"' in html


def test_bell_sends_csrf_for_mutating_requests() -> None:
    """Mark-read requests must carry the page token through the bell root."""
    from lexigram.ui import NotificationBell

    html = str(NotificationBell(csrf_token="csrf-123"))

    assert 'data-csrf-token="csrf-123"' in html
    assert "X-CSRF-Token" in html
    assert "this.$el.dataset.csrfToken" in html


def test_bell_inbox_footer_only_with_inbox_url() -> None:
    """View-all footer should render only when inbox_url is set."""
    from lexigram.ui import NotificationBell

    with_footer = str(NotificationBell(inbox_url="/admin/notifications"))
    without_footer = str(NotificationBell())

    assert "View all notifications" in with_footer
    assert 'href="/admin/notifications"' in with_footer
    assert "View all notifications" not in without_footer


def test_bell_respects_max_display() -> None:
    """Bell should cap the in-memory notification list at max_display."""
    from lexigram.ui import NotificationBell

    html = str(NotificationBell(max_display=5))

    assert "this.notifications.length > 5" in html

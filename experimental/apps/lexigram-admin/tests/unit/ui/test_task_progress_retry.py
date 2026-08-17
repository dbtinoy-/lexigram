from lexigram.ui.core.base import render_to_string
from lexigram.ui import TaskProgress


def test_task_progress_renders_retry_as_action_button():
    html = render_to_string(TaskProgress(task_id="t-123", title="Working..."))

    # The Retry button should exist
    assert "Retry" in html
    # ActionButton base classes
    assert "inline-flex items-center" in html
    # Uses hx-on-click to trigger client-side reload
    assert "hx-on-click" in html
    assert "window.location.reload" in html

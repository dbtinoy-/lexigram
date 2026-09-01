from __future__ import annotations

import re
from typing import Any

from lexigram.logging import get_logger
from lexigram.ui import ActionButton, Component, el
from lexigram.ui.core.js import js_json, js_string
from lexigram.ui.core.url import is_safe_navigation_url

logger = get_logger(__name__)


class TaskProgress(Component):
    """Real-time progress tracking component with SSE updates.

    Connects to a Server-Sent Events endpoint to display live progress
    of a background task. Shows progress bar, status, and messages.

    Args:
        task_id: Unique identifier for the task
        title: Progress dialog title
        auto_close: Whether to auto-close on completion
        on_complete: URL to redirect to or JS callback on completion
        stream_url: Custom SSE endpoint URL (defaults to /admin/progress/{task_id}/stream)
    """

    def __init__(
        self,
        task_id: str,
        title: str = "Processing...",
        auto_close: bool = False,
        on_complete: str | None = None,
        stream_url: str | None = None,
        **props: Any,
    ) -> None:
        super().__init__(
            task_id=task_id,
            title=title,
            auto_close=auto_close,
            on_complete=on_complete,
            stream_url=stream_url,
            **props,
        )
        self.task_id = task_id
        self.title = title
        self.auto_close = auto_close
        self.on_complete = on_complete
        self.stream_url = stream_url or f"/admin/progress/{task_id}/stream"

    #: A callback name must look like a plain JS identifier path
    #: (``notify`` or ``app.onDone``). Anything else -- call syntax,
    #: operators, quotes -- is rejected rather than escaped, because the
    #: value is executed, not displayed, and there is no encoding that makes
    #: arbitrary code safe to run.
    _CALLBACK_NAME = re.compile(r"^[A-Za-z_$][\w$]*(?:\.[A-Za-z_$][\w$]*)*$")

    def _on_complete_js(self) -> str:
        """Return the JS to run when the task completes.

        ``on_complete`` was previously concatenated straight into the script
        body, so a caller string became executable code and a URL was
        embedded in a hand-quoted literal. Both are now constrained: a path
        is emitted as a properly encoded string literal assigned to
        ``location.href``, and a callback is admitted only if it is a bare
        identifier path.
        """
        target = self.on_complete
        if not target:
            return ""

        if target.startswith("/"):
            if not is_safe_navigation_url(target):
                logger.warning(
                    "task_progress_unsafe_redirect",
                    on_complete=target,
                )
                return ""
            return f"window.location.href = {js_string(target)};"

        if not self._CALLBACK_NAME.match(target):
            logger.warning(
                "task_progress_rejected_callback",
                on_complete=target,
            )
            return ""
        return f"{target}();"

    def render(self) -> Any:
        # Alpine.js data for managing state.
        #
        # `init` and `destroy` are JavaScript method bodies, not data, so
        # this cannot be serialised with json.dumps -- that would quote them
        # into strings and Alpine would never call them. The object literal
        # is assembled explicitly below instead; only the genuinely
        # data-valued entries go through js_json.
        state = {
            "status": "pending",
            "progress": 0,
            "message": "Initializing...",
            "error": None,
            "eventSource": None,
        }
        init_body = f"""
                this.eventSource = new EventSource({js_string(self.stream_url)});

                this.eventSource.addEventListener('progress', (e) => {{
                    const data = JSON.parse(e.data);
                    this.status = data.status;
                    this.progress = data.progress;
                    this.message = data.message || 'Processing...';

                    if (data.status === 'completed') {{
                        this.eventSource.close();
                        {self._on_complete_js()}
                    }} else if (data.status === 'failed') {{
                        this.error = data.error || 'Task failed';
                        this.eventSource.close();
                    }}
                }});

                this.eventSource.addEventListener('error', (e) => {{
                    this.error = 'Connection lost';
                    this.eventSource.close();
                }});

                const obs = new MutationObserver(() => {{
                    if (!this.$el.isConnected) {{
                        obs.disconnect();
                        if (this.eventSource) this.eventSource.close();
                    }}
                }});
                obs.observe(document.body, {{ childList: true, subtree: true }});
        """
        destroy_body = """
                if (this.eventSource) {
                    this.eventSource.close();
                }
        """

        # Data entries via js_json (so None becomes null, not Python's
        # None); method bodies spliced in as code.
        state_entries = ",\n".join(
            f"    {js_string(key)}: {js_json(value)}" for key, value in state.items()
        )
        alpine_data = (
            "{\n"
            f"{state_entries},\n"
            f"    init() {{{init_body}\n    }},\n"
            f"    destroy() {{{destroy_body}\n    }}\n"
            "}"
        )

        # Status icon based on current status
        status_icon = el(
            "div",
            el(
                "svg",
                el(
                    "path",
                    d="M12 2v4m0 12v4M4.93 4.93l2.83 2.83m8.48 8.48l2.83 2.83M2 12h4m12 0h4M4.93 19.07l2.83-2.83m8.48-8.48l2.83-2.83",
                    stroke_linecap="round",
                    stroke_linejoin="round",
                    stroke_width="2",
                ),
                class_="w-12 h-12 text-primary-600 dark:text-primary-400 animate-spin",
                fill="none",
                viewBox="0 0 24 24",
                stroke="currentColor",
                x_show="status === 'pending' || status === 'running'",
            ),
            el(
                "svg",
                el(
                    "path",
                    d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z",
                    stroke_linecap="round",
                    stroke_linejoin="round",
                    stroke_width="2",
                ),
                class_="w-12 h-12 text-success",
                fill="none",
                viewBox="0 0 24 24",
                stroke="currentColor",
                x_show="status === 'completed'",
            ),
            el(
                "svg",
                el(
                    "path",
                    d="M12 8v4m0 4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z",
                    stroke_linecap="round",
                    stroke_linejoin="round",
                    stroke_width="2",
                ),
                class_="w-12 h-12 text-destructive",
                fill="none",
                viewBox="0 0 24 24",
                stroke="currentColor",
                x_show="status === 'failed'",
            ),
            class_="mb-4",
        )

        # Progress bar
        progress_bar = el(
            "div",
            el(
                "div",
                el(
                    "div",
                    class_="h-full bg-primary-600 dark:bg-primary-400 rounded-full transition-all duration-300",
                    x_bind__style="'width: ' + progress + '%'",
                ),
                class_="w-full bg-muted rounded-full h-2.5",
            ),
            el(
                "div",
                el(
                    "span",
                    x_text="progress + '%'",
                    class_="text-sm font-semibold text-foreground",
                ),
                class_="mt-2 flex justify-between items-center",
            ),
            class_="mb-4",
            x_show="status !== 'failed'",
        )

        # Message display
        message_display = el(
            "div",
            el(
                "p",
                x_text="message",
                class_="text-sm text-muted-foreground text-center",
            ),
            class_="mb-4",
        )

        # Error display
        error_display = el(
            "div",
            el(
                "div",
                el(
                    "p",
                    "An error occurred:",
                    class_="font-semibold text-destructive mb-2",
                ),
                el(
                    "p",
                    x_text="error",
                    class_="text-sm text-destructive",
                ),
                el(
                    "div",
                    ActionButton(
                        label="Retry",
                        color="danger",
                        size="md",
                        hx_on_click="window.location.reload()",
                    ).render(),
                    class_="mt-4",
                ),
                class_="p-4 bg-destructive/10 border border-destructive/30 rounded-lg",
            ),
            x_show="error !== null",
        )

        return el(
            "div",
            el(
                "div",
                el(
                    "div",
                    el(
                        "h3",
                        self.title,
                        class_="text-lg font-semibold text-foreground mb-6 text-center",
                    ),
                    status_icon,
                    progress_bar,
                    message_display,
                    error_display,
                    class_="bg-card rounded-xl shadow-lg p-8 max-w-md w-full",
                ),
                class_="flex items-center justify-center min-h-screen p-4",
            ),
            x_data=alpine_data,
            x_init="init()",
            **{"x-on:beforeunload.window": "destroy()"},
            class_="fixed inset-0 bg-muted/75 dark:bg-background/75 backdrop-blur-sm z-50",
        )

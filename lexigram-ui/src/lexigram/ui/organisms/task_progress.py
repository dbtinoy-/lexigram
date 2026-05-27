from __future__ import annotations

from typing import Any

from lexigram.ui import ActionButton, Component, el


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
        **props,
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

    def render(self) -> Any:
        # Alpine.js data for managing state
        alpine_data = {
            "status": "pending",
            "progress": 0,
            "message": "Initializing...",
            "error": None,
            "eventSource": None,
            "init": f"""
                this.eventSource = new EventSource('{self.stream_url}');

                this.eventSource.addEventListener('progress', (e) => {{
                    const data = JSON.parse(e.data);
                    this.status = data.status;
                    this.progress = data.progress;
                    this.message = data.message || 'Processing...';

                    if (data.status === 'completed') {{
                        this.eventSource.close();
                        {'window.location.href = "' + self.on_complete + '";' if self.on_complete and self.on_complete.startswith("/") else ""}
                        {self.on_complete + "();" if self.on_complete and not self.on_complete.startswith("/") else ""}
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
            """,
            "destroy": """
                if (this.eventSource) {
                    this.eventSource.close();
                }
            """,
        }

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
            x_data=f"{alpine_data}",
            x_init="init()",
            x_on_before_unload_window="destroy()",
            class_="fixed inset-0 bg-muted/75 dark:bg-background/75 backdrop-blur-sm z-50",
        )

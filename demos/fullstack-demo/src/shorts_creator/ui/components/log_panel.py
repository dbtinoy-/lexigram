from lexigram.ui import el


def LogPanel():
    return (
        '<link rel="stylesheet" href="/static/css/log-panel.css">'
        '<script src="/static/js/log-panel.js"></script>'
        + str(
            el(
                "div",
                el(
                    "div",
                    el(
                        "div",
                        el("h3", "Operation Log"),
                        el(
                            "button",
                            "Clear",
                            class_="text-[10px] px-2 py-0.5 rounded bg-secondary hover:bg-secondary text-muted-foreground font-mono transition-colors mr-2",
                            onclick="window.__lp.clearLog()",
                        ),
                        el(
                            "button",
                            "\u00d7",
                            class_="lp-close",
                            onclick="document.getElementById('log-panel').classList.remove('open')",
                        ),
                        class_="lp-header",
                    ),
                    el("div", id="log-entries"),
                    id="log-panel",
                    class_="w-80 bg-card/95 translate-x-full",
                ),
                el(
                    "button",
                    el("span", "\u2699"),
                    el("span", "Log"),
                    el(
                        "span",
                        "0",
                        id="lp-badge",
                        style="display:none",
                        class_="lp-badge",
                    ),
                    id="log-toggle",
                    onclick="window.__lp.toggle()",
                ),
            )
        )
    )

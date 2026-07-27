from lexigram.ui import el
from markupsafe import Markup


def ProviderCard(provider: dict) -> str:
    name = provider["name"]
    model = provider["model"]
    status = provider.get("status", "unknown")

    dot = {
        "healthy": "bg-success shadow-[0_0_8px_rgb(var(--color-success-channels)_/_0.5)]",
        "unconfigured": "bg-warning",
        "disabled": "bg-muted-foreground",
        "error": "bg-destructive",
        "unknown": "bg-muted-foreground",
    }.get(status, "bg-muted-foreground")

    status_label = {
        "healthy": "Ready",
        "unconfigured": "Unconfigured",
        "disabled": "Disabled",
        "error": "Error",
        "unknown": "Unknown",
    }.get(status, "Unknown")

    status_badge_style = {
        "healthy": "text-success border-success/50 bg-success/40",
        "unconfigured": "text-warning border-warning/50 bg-warning/40",
        "disabled": "text-muted-foreground border-border/50 bg-card/50",
        "error": "text-destructive border-destructive/50 bg-destructive/40",
    }.get(status, "text-muted-foreground border-border/50 bg-card/50")

    return Markup(
        el(
            "div",
            el(
                "div",
                el("span", class_=f"inline-block w-2.5 h-2.5 rounded-full {dot} mr-3 shrink-0"),
                el(
                    "div",
                    el("span", model, class_="text-foreground font-semibold text-sm font-mono"),
                    el(
                        "span",
                        name,
                        class_="text-muted-foreground text-[10px] font-mono ml-2 capitalize",
                    ),
                    class_="flex flex-wrap items-center gap-1",
                ),
                class_="flex items-center",
            ),
            el(
                "div",
                el(
                    "span",
                    status_label,
                    class_=f"text-xs font-mono font-medium px-2.5 py-1 rounded-full border {status_badge_style}",
                ),
                class_="flex items-center ml-3",
            ),
            class_="flex items-center justify-between p-4 bg-card/90 rounded-xl border border-border/80 mb-2.5 shadow-sm hover:border-border transition-colors",
        )
    )

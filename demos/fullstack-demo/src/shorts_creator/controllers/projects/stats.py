from lexigram.ui import el
from markupsafe import Markup


def _proj_stat(value: str, label: str, color: str) -> str:
    return Markup(
        str(
            el(
                "div",
                el("span", value, class_=f"text-lg font-bold font-mono {color}"),
                el("span", label, class_="text-[10px] font-mono text-muted-foreground block"),
                class_="flex flex-col items-start",
            )
        )
    )

"""ActionButton — the single shared button component for htmx actions.

Every button that issues a request gets:
- a reserved spinner slot (no layout shift while loading),
- hx-disabled-elt="this" (no double submits),
- a consistent variant/size class map.
"""

from lexigram.ui import el
from markupsafe import Markup

from shorts_creator.ui.icons import spinner

VARIANTS = {
    "primary": (
        "bg-primary hover:bg-primary/90 text-primary-foreground shadow-sm shadow-primary/40"
    ),
    "success": (
        "bg-success hover:bg-success/90 text-success-foreground shadow-lg shadow-success/40"
    ),
    "ghost": ("bg-secondary hover:bg-secondary/80 text-foreground border border-border/50"),
    "outline": (
        "bg-card/40 text-muted-foreground hover:text-foreground border border-border/60 "
        "hover:border-border/80"
    ),
    "danger": (
        "bg-destructive/40 hover:bg-destructive/40 text-destructive border border-destructive/50"
    ),
}

SIZES = {
    "sm": "px-3 py-1.5 rounded-lg text-xs",
    "md": "px-4 py-2 rounded-lg text-xs",
    "lg": "px-6 py-3.5 rounded-xl text-sm",
}


def ActionButton(
    label: str,
    *,
    icon: str = "",
    variant: str = "primary",
    size: str = "sm",
    type: str = "button",
    form: str = "",
    hx_get: str = "",
    hx_post: str = "",
    hx_put: str = "",
    hx_delete: str = "",
    hx_target: str = "",
    hx_swap: str = "",
    hx_vals: str = "",
    hx_include: str = "",
    hx_confirm: str = "",
    onclick: str = "",
    disabled: bool = False,
    id: str = "",
    title: str = "",
    class_extra: str = "",
) -> str:
    hx_attrs = {}
    if hx_get:
        hx_attrs["hx_get"] = hx_get
    if hx_post:
        hx_attrs["hx_post"] = hx_post
    if hx_put:
        hx_attrs["hx_put"] = hx_put
    if hx_delete:
        hx_attrs["hx_delete"] = hx_delete
    if hx_target:
        hx_attrs["hx_target"] = hx_target
    if hx_swap:
        hx_attrs["hx_swap"] = hx_swap
    if hx_vals:
        hx_attrs["hx_vals"] = hx_vals
    if hx_include:
        hx_attrs["hx_include"] = hx_include
    if hx_confirm:
        hx_attrs["hx_confirm"] = hx_confirm
    if any((hx_post, hx_put, hx_delete)):
        hx_attrs["hx_disabled_elt"] = "this"

    return Markup(
        str(
            el(
                "button",
                *(
                    part
                    for part in (icon, el("span", label, class_="font-semibold") if label else "")
                    if part
                ),
                el(
                    "span",
                    spinner("sm", indicator=True),
                    class_="w-4 h-4 shrink-0 grid place-items-center",
                ),
                id=id or None,
                title=title or None,
                type=type,
                form=form or None,
                onclick=onclick or None,
                disabled=disabled or None,
                class_=(
                    f"inline-flex items-center justify-center gap-2 select-none transition-all duration-200 "
                    f"disabled:opacity-50 disabled:cursor-not-allowed "
                    f"{VARIANTS.get(variant, VARIANTS['primary'])} {SIZES.get(size, SIZES['sm'])} {class_extra}"
                ),
                **hx_attrs,
            )
        )
    )

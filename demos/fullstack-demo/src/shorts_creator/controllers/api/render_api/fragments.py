from lexigram.ui import el
from lexigram.web import HTMLContent

from shorts_creator.contracts.issues import ContractIssue
from shorts_creator.ui.icons import alert, check


def _RenderError(msg):
    return str(
        el(
            "div",
            alert(),
            el("span", f" {msg}", class_="ml-2 font-medium"),
            class_="flex items-center p-4 bg-destructive/40 rounded-xl border border-destructive/50 text-destructive text-xs font-mono shadow-sm",
        )
    )


def _RenderSuccess(path):
    return str(
        el(
            "div",
            check(),
            el(
                "div",
                el("span", " Render Complete!", class_="text-success font-semibold text-sm"),
                el(
                    "p",
                    f"Exported Output: {path}",
                    class_="text-muted-foreground text-xs mt-0.5 font-mono truncate",
                ),
                class_="ml-2.5",
            ),
            class_="flex items-center p-4 bg-success/40 rounded-xl border border-success/50 text-success shadow-sm",
        )
    )


def _ProfileErrorFragment(errors: dict[str, str]):
    details = "; ".join(f"{key}: {msg}" for key, msg in errors.items())
    return HTMLContent(_RenderError(f"Project settings are invalid - {details}"))


def _PairErrorFragment(issues: list[ContractIssue]):
    details = "; ".join(f"{issue.code}: {issue.message}" for issue in issues)
    return HTMLContent(_RenderError(f"Topic/format contract violation - {details}"))

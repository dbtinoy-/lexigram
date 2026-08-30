"""Public-API guard test.

Every symbol in CANONICAL_API_SYMBOLS must be importable from `lexigram.ui`.
This test prevents silent drift: if a downstream package (like lexigram-admin)
depends on a name, that name must live on the package surface — never via
a deep-path import.
"""
from __future__ import annotations

import importlib
import os
import re

import pytest

# Symbols the public API promises. Grouped by responsibility for readability.
# Order does not matter; the test resolves each name through `lexigram.ui`.
CANONICAL_API_SYMBOLS: list[str] = [
    # Core primitives
    "Component", "Element", "RawHTML", "el", "raw", "render_to_string",
    # Context
    "UIContext", "get_ui_context", "reset_ui_context", "set_ui_context",
    # Zones
    "Zone", "Zones", "SwapMode",
    # Icons
    "get_icon", "IconDefinition", "IconLibrary",
    # HTMX namespaces
    "htmx", "helpers", "sse",
    "HtmxActionResponse",
    # Exceptions & errors
    "UIError", "ErrorCategory", "FieldError", "ErrorResponse",
    "validation_error", "not_found_error", "permission_error",
    "server_error", "timeout_error", "render_validation_errors",
    "htmx_error_response",
    # DI
    "UIModule", "UIProvider",
    # Protocols
    "RenderableProtocol",
    # Decorators
    "component",
    # Hooks
    "UIComponentRenderedHook", "UITemplateRenderedHook",
    # Accessibility
    "AriaAttrs", "AriaLive", "AriaRole", "SkipLink", "announce",
    "announce_table_update", "button_aria", "dialog_aria", "header_aria",
    "keyboard_navigation_script", "row_aria", "search_aria", "table_aria",
    # Config
    "UIConfig", "DebounceConfig", "HTMLDocumentConfig", "BaseLayoutConfig",
    "HeadConfig", "FooterConfig", "ToastConfig",
    # Atoms — primitives
    "Button", "SubmitButton", "Badge", "Spinner", "Icon",
    "Divider", "Link", "Label", "Fieldset", "FileUpload",
    "ProgressBar", "Skeleton", "Switch", "Tooltip",
    "MarkdownEditor", "RichEditor",
    # Atoms — layout primitives
    "Aside", "Col", "Container", "Grid", "Row", "Stack",
    # Atoms — inputs
    "AbstractInput", "Input", "TextInput", "PasswordInput", "EmailInput",
    "TextArea", "NumberInput", "Slider", "DateInput", "TimePicker",
    "Select", "MultiSelect", "NativeMultiSelect", "LazySelect",
    "CheckboxList", "Radio", "BelongsTo", "MorphTo",
    "Checkbox", "Toggle",
    "ColorPicker", "Hidden", "KeyValueField", "Rating", "TagsInput",
    "AvatarUpload", "MultiFileUpload",
    # Molecules
    "Alert", "SimpleAlert", "Breadcrumbs", "Card", "Dropdown",
    "EmptyState", "ErrorState", "FormActions", "FormField", "FieldSchema",
    "InputGroup", "LoadingOverlay", "MetricCard", "Modal", "Popover",
    "RichSelect", "Section", "StatCard", "Tabs", "TabPanel",
    # Molecules — toasts
    "InlineToast", "ServerToastChannel",
    "ToastData", "ToastType", "flash_to_toast",
    # Molecules — realtime / scroll
    "InfiniteScrollTrigger", "VirtualScroll", "RealTimeFeed", "LiveCounter",
    # Molecules — Builder
    "Builder",
    # Organisms
    "Form", "Repeater", "ActivityFeed", "SlideOver",
    "AdminCard", "PageLayout",
    # Performance
    "RenderCache", "ResponseOptimizer", "add_htmx_timing_header",
    "debounced_search_attrs", "infinite_scroll_trigger",
    "lazy_load_placeholder", "measure_render_time",
    # Observability
    "MetricsCollector", "MetricProtocol", "MetricType",
]


@pytest.mark.parametrize("name", CANONICAL_API_SYMBOLS)
def test_public_api_symbol_resolves(name: str) -> None:
    """Every canonical name must resolve from `lexigram.ui`.

    If this test fails, either:
    1. Add the symbol to `LAZY_IMPORTS` in `lexigram/ui/exports/lazy.py`, OR
    2. Remove it from CANONICAL_API_SYMBOLS if it should not be public.

    Never let a downstream package deep-path-import what should be public.
    """
    ui = importlib.import_module("lexigram.ui")
    resolved = getattr(ui, name)
    assert resolved is not None, f"`lexigram.ui.{name}` resolved to None"


def test_canonical_list_has_no_duplicates() -> None:
    assert len(CANONICAL_API_SYMBOLS) == len(set(CANONICAL_API_SYMBOLS)), (
        "CANONICAL_API_SYMBOLS contains duplicates"
    )


def test_dir_includes_all_canonical_names() -> None:
    """`dir(lexigram.ui)` should surface every canonical name for IDEs."""
    ui = importlib.import_module("lexigram.ui")
    dir_names = set(dir(ui))
    missing = set(CANONICAL_API_SYMBOLS) - dir_names
    assert not missing, f"Missing from dir(): {sorted(missing)}"


def _load_lazy_imports() -> set[str]:
    """Load the set of public symbols from the lazy import map."""
    repo_root = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    ui_init = os.path.join(
        repo_root, "lexigram-ui", "src", "lexigram", "ui", "exports", "lazy.py"
    )
    with open(ui_init) as f:
        content = f.read()
    match = re.search(r"LAZY_IMPORTS.*?=\s*\{", content)
    assert match, "_LAZY_IMPORTS dict not found"
    start = match.end()
    depth = 1
    i = start
    while i < len(content) and depth > 0:
        if content[i] == "{":
            depth += 1
        elif content[i] == "}":
            depth -= 1
        elif content[i] in "\"'":
            q = content[i]; i += 1
            while i < len(content) and content[i] != q:
                if content[i] == "\\":
                    i += 1
                i += 1
        i += 1
    dict_text = content[start : i - 1]
    keys: set[str] = set()
    for m in re.finditer(r'"([^"]+)"\s*:', dict_text):
        keys.add(m.group(1))
    for m in re.finditer(r"'([^']+)'\s*:", dict_text):
        keys.add(m.group(1))
    return keys


DEEP_IMPORT_RE = re.compile(
    r"^from lexigram\.ui\.(?:atoms|molecules|organisms|core)\.\w+\s+import\s+(.+)$",
)


def test_no_phantom_deep_imports() -> None:
    """All module-level deep imports from lexigram.ui subpackages should use the
    public surface instead, unless the symbol is genuinely not public.

    This test prevents a downstream package from silently depending on
    a lexigram.ui internal without the author of lexigram.ui knowing.
    """
    public = _load_lazy_imports()
    repo_root = os.path.join(os.path.dirname(__file__), "..", "..", "..")
    packages = ["lexigram-admin", "lexigram-web"]
    violations: list[str] = []

    for pkg in packages:
        src_dir = os.path.join(repo_root, pkg, "src")
        if not os.path.isdir(src_dir):
            continue
        for root, dirs, files in os.walk(src_dir):
            for fname in files:
                if not fname.endswith(".py") or fname == "__init__.py":
                    continue
                fpath = os.path.join(root, fname)
                with open(fpath) as f:
                    for lineno, line in enumerate(f, 1):
                        if line[0] in (" ", "\t"):
                            continue
                        m = DEEP_IMPORT_RE.match(line.strip())
                        if not m:
                            continue
                        parts = [p.strip() for p in m.group(1).split(",") if p.strip()]
                        for p in parts:
                            raw = p.split(" as ")[0].strip()
                            if raw in public:
                                violations.append(
                                    f"{fpath}:{lineno}: "
                                    f"`{raw}` should come from `from lexigram.ui import ...` "
                                    f"(in LAZY_IMPORTS)"
                                )

    assert not violations, (
        f"Found {len(violations)} module-level deep imports of public symbols:\n"
        + "\n".join(sorted(violations))
    )

from __future__ import annotations

from collections.abc import Iterable
import html
import importlib
import re
from types import TracebackType
from typing import Any, Self, cast

from markupsafe import Markup

from lexigram.logging import get_logger

logger = get_logger(__name__)

# Prefer a real `htpy` module when available, but tolerate environments
# without it (tests, minimal installs). We expose an `el` factory that
# constructs a real htpy element when possible, otherwise falls back to
# our lightweight `Element` implementation.

try:
    _htpy = importlib.import_module("htpy")
except ImportError:  # pragma: no cover - networks / minimal envs
    _htpy = None  # type: ignore[assignment]


def _is_htpy_element(el: Any) -> bool:
    # Only consider objects that provide an explicit HTML conversion
    # method (``__html__``). Components also implement ``render`` so
    # checking for ``render`` would misclassify them as htpy elements.
    return hasattr(el, "__html__")


class Element:
    """A lightweight, structured HTML element compatible with htpy.

    This provides a small subset of behaviour we need: HTML attribute
    escaping, boolean attributes, self-closing tag handling and a stable
    `__html__`/`__str__` API so our `render_to_string` function can
    consistently produce HTML regardless of whether `htpy` is present.
    """

    SELF_CLOSING = {"input", "img", "br", "hr", "meta", "link"}

    def __init__(self, tag: str, *children: Any, **attrs: Any) -> None:
        self.tag = tag
        self.children = list(children)
        self.attrs = attrs

        # If leading children are dicts, use them as attributes (htpy-style)
        while self.children and isinstance(self.children[0], dict):
            self.attrs.update(self.children.pop(0))

        # Auto-add type="button" for HTMX-enabled buttons to avoid accidental form submits
        if self.tag == "button":
            if "type" not in self.attrs:
                # Detect HTMX-style attributes (pythonic `hx_` names)
                if any(k.startswith("hx") for k in self.attrs):
                    self.attrs["type"] = "button"

            # Remove automatic `hx_trigger="load"` to prefer manual checks
            for k in list(self.attrs.keys()):
                if k in ("hx_trigger", "hx-trigger"):
                    if str(self.attrs[k]) == "load":
                        del self.attrs[k]

        # Support Streamlit-like `with` usage by adding ourselves to the current context
        add_child_to_current(self)

    def __enter__(self) -> Self:
        _context_stack.append(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        if _context_stack and _context_stack[-1] is self:
            _context_stack.pop()

    def __html__(self) -> str:
        parts: list[str] = [f"<{self.tag}"]
        for k, v in self.attrs.items():
            # Map pythonic kwarg names like `class_` to `class`, `for_` to `for`,
            # and convert internal underscores to hyphens so `hx_post` -> `hx-post`.
            if k == "class_":
                attr_name = "class"
            elif k.endswith("_") and "_" not in k[:-1]:
                # Handles `for_`, `id_` (reserved words or trailing underscores)
                attr_name = k[:-1]
            else:
                attr_name = k.replace("_", "-")

            if v is True:
                parts.append(f" {attr_name}")
            elif v is False or v is None:
                continue
            else:
                parts.append(f' {attr_name}="{html.escape(str(v), quote=True)}"')

        if self.tag in self.SELF_CLOSING:
            parts.append(" />")
            return "".join(parts)

        parts.append(">")

        for c in self.children:
            parts.append(_render_child(c))

        parts.append(f"</{self.tag}>")
        return "".join(parts)

    def __str__(self) -> str:  # pragma: no cover - exercised indirectly
        return self.__html__()


class RawHTML:
    """Wrapper for raw HTML strings that should be included verbatim.

    Instances implement ``__html__`` so they are detected as htpy-like
    elements and their contents are not escaped when inserted as children.
    """

    def __init__(self, value: str) -> None:
        self.value = value

    def __html__(self) -> str:
        return str(self.value)


def raw(value: str) -> RawHTML:
    return RawHTML(value)


def el(tag: str, *children: Any, **attrs: Any) -> Any:
    """Construct an element using `htpy` when available, otherwise
    return an `Element` fallback that implements `__html__`.

    For self-closing tags we prefer our local Element to ensure consistent
    output (including trailing slash), even when `htpy` is installed.
    """
    # Ensure deterministic, self-closing rendering for known empty tags
    if tag in Element.SELF_CLOSING:
        return Element(tag, *children, **attrs)

    # We always use our local Element for blocks that might be used with `with`,
    # even if htpy is present, to ensure they support the context manager protocol.
    return Element(tag, *children, **attrs)


def _render_child(child: Any) -> str:
    """Render one Element child under the framework's escaping policy.

    Policy — *strings are data, elements are structure*:

    - Plain strings are escaped (they are text content). This includes
      plain strings returned by ``Component.render()``: a component is
      resolved first and its string result is treated as data.
    - ``Markup`` (markupsafe), ``RawHTML`` (via ``raw()``), ``Element``
      and any other ``__html__``-bearing object pass through verbatim —
      those are explicit opt-outs signalling pre-rendered HTML.
    - Iterables are rendered element-wise under the same policy.

    This closes the previous inconsistency where a ``Component`` child
    bypassed escaping entirely (``render_to_string`` returns strings
    verbatim), so a component whose ``render()`` returned
    ``"<b>" + user_input + "</b>"`` injected unescaped markup.
    """
    if child is None:
        return ""
    if isinstance(child, str):
        if isinstance(child, Markup):
            return child
        return html.escape(child, quote=False)
    if isinstance(child, Component):
        as_child_result = child._render_as_child()
        if as_child_result is not None:
            return _render_child(as_child_result)
        return _render_child(child.render())
    # Elements / RawHTML / htpy elements and any other __html__-bearing
    # object are structure: render verbatim (escaping already happened at
    # their own boundaries). Must be checked before Iterable because htpy
    # elements are iterable (for `with` support).
    if _is_htpy_element(child):
        return render_to_string(child)
    if isinstance(child, Iterable) and not isinstance(child, (bytes, dict)):
        return "".join(_render_child(item) for item in child)
    return render_to_string(child)


# Context stack to support Streamlit-like `with` usage
_context_stack: list[Any] = []
_no_context: bool = False


class NoContext:
    """Context manager to temporarily disable auto-registration of components."""

    def __enter__(self) -> Any:
        global _no_context
        self.old = _no_context
        _no_context = True

    def __exit__(self, *args: object) -> Any:
        global _no_context
        _no_context = self.old


def add_child_to_current(child: Any) -> None:
    """If a component is active in a `with` context, append child to it."""
    if _context_stack and not _no_context:
        parent = _context_stack[-1]
        parent.children.append(child)


class Component:
    """Base UI Component for lexigram-admin (HTPy-backed).

    Subclasses implement `render()` which returns either a string
    or an htpy element. `render_to_string` converts to HTML.

    Components support Streamlit-style `with` usage via context manager
    methods: entering the context makes the component the current parent
    for subsequent calls to `add_child_to_current` or manual appends.
    """

    def __init__(self, *children: Any, as_child: bool = False, **props: Any) -> None:
        self.as_child = as_child
        self.props = props
        self.children: list[Any] = (
            list(children) if children else list(props.pop("children", []))
        )
        # Support Streamlit-like `with` usage by adding ourselves to the current context
        add_child_to_current(self)
        self.on_mount()

    def _render_as_child(self) -> str | Any:
        """Render by delegating to the first child when ``as_child`` is True."""
        if not self.as_child or not self.children:
            return None  # signal to fall through to normal render

        child = self.children[0]
        # Local import to avoid circular import (slot.py imports Component from here)
        from lexigram.ui.core.slot import Slot

        if isinstance(child, Slot):
            return child.render()

        if isinstance(child, Component):
            # Merge parent's non-conflicting props into the child
            for key, value in self.props.items():
                if key not in child.props:
                    child.props[key] = value
            return child.render()

        return str(child)

    def __init_subclass__(cls, **kwargs: Any) -> None:
        super().__init_subclass__(**kwargs)
        # Handle auto-registration if @Injectable was used
        if hasattr(cls, "_injectable_config"):
            # Registration will happen during provider discovery
            pass

    def on_mount(self) -> None:
        """Lifecycle hook called when component is instantiated."""

    def __enter__(self) -> Self:
        _context_stack.append(self)
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        # Pop self from the stack if it's the active context
        if _context_stack and _context_stack[-1] is self:
            _context_stack.pop()

    def add(self, *children: Any) -> Component:
        """Fluent API to add children to this component."""
        self.children.extend(children)
        return self

    def render(self) -> str | Any:
        raise NotImplementedError

    def __html__(self) -> str:
        # Check asChild delegation first
        as_child_result = self._render_as_child()
        if as_child_result is not None:
            rendered = as_child_result
        else:
            from lexigram.ui.config import (
                UIConfig,  # lazy to avoid circular at import time
            )

            try:
                cfg = UIConfig()  # use defaults; provider may supply a richer instance
            except Exception as e:  # noqa: BLE001
                logger.debug("ui_config_load_failed", error=str(e))
                cfg = None

            rendered = self.render()
            debug = getattr(cfg, "debug_components", False)
            if debug:
                component_name = type(self).__name__
                logger.debug("component.render", component=component_name)
                # Inject data-component attribute on the outermost element.
                html_str = render_to_string(rendered)
                # Prepend data-component as an HTML comment marker that
                # does not mutate the element tree (safe, non-intrusive).
                return (
                    f'<!-- data-component="{html.escape(component_name)}" -->{html_str}'
                )
        return render_to_string(rendered)

    def __str__(self) -> str:
        return self.__html__()


def render_to_string(value: str | Any) -> str:
    """Render a component or htpy element to an HTML string.

    This performs a best-effort conversion: strings are returned verbatim,
    htpy elements are converted if they provide a renderer, iterables are
    flattened by rendering each child and concatenating the results, and
    component instances are rendered via their `render()` method.
    """
    # None becomes empty string
    if value is None:
        return ""

    # Strings are returned verbatim. Escaping happens at the Element/htpy
    # attribute layer when content is inserted into HTML. To include
    # pre-rendered HTML safely, use RawHTML (via raw()) which signals intent.
    if isinstance(value, str):
        return value

    # Iterables (lists/tuples/generators) are rendered element-wise. We
    # explicitly exclude `bytes`/`dict` as they are not HTML sequences.
    if isinstance(value, Iterable) and not isinstance(value, (str, bytes, dict)):
        # Check if the value has iter_chunks method (deprecation path)
        if hasattr(value, "iter_chunks"):
            return "".join(render_to_string(chunk) for chunk in value.iter_chunks())
        return "".join(render_to_string(v) for v in value)

    # Note: we check for Component first to avoid infinite recursion if
    # Component implements __html__ (which it does, calling this function).
    if isinstance(value, Component):
        return render_to_string(value.render())

    if _is_htpy_element(value):
        try:
            # Prefer the explicit HTML representation if available
            return cast("str", value.__html__())
        except (AttributeError, TypeError):
            from lexigram.logging import get_logger

            logger = get_logger(__name__)
            logger.exception("htpy element __html__() raised an exception")

            try:
                return str(value)
            except (TypeError, ValueError) as e:
                logger.debug(
                    "str() conversion failed for htpy element; falling back to repr: %s",
                    e,
                    exc_info=True,
                )
                return repr(value)

    # fallback for objects with render method but not inheriting from Component
    if hasattr(value, "render") and callable(value.render):
        return render_to_string(value.render())

    return html.escape(str(value))


# ---------------------------------------------------------------------------
# Developer-experience helpers for the "raw HTML" failure mode.
#
# The most common admin bug: a custom renderer (e.g. a ``Column.render()``
# override) returns a pre-built HTML *string*. Under the escaping policy
# above that string is treated as data and escaped, so the browser shows
# the markup as literal text (``&lt;span class=...&gt;...``). These helpers
# detect that situation at the render boundaries and log a one-time warning
# telling the developer exactly what to change.
# ---------------------------------------------------------------------------

_HTML_TAG_RE = re.compile(r"</?[a-zA-Z][a-zA-Z0-9-]*\b[^>]*>")

#: (origin, snippet-prefix) pairs already warned about — avoids log spam on
#: every cell of every request.
_warned_html_strings: set[tuple[str, str]] = set()

#: Cached debug_components flag; see _debug_components_enabled.
_debug_components_cache: bool | None = None


def looks_like_html(value: Any) -> bool:
    """Heuristic: does this string look like it contains an HTML tag?"""
    return isinstance(value, str) and bool(_HTML_TAG_RE.search(value))


def warn_html_string_render(
    origin: str,
    snippet: Any,
    *,
    fix: str = (
        "return an element built with el(...), or wrap the string in "
        "raw()/Markup when pre-rendered HTML is intended"
    ),
) -> None:
    """Warn (once per origin/snippet) that a renderer returned an HTML string.

    The string will be escaped by the element layer, so the browser shows
    literal markup instead of rendered HTML. Emitting a warning here turns a
    confusing UI bug into an actionable log message.

    Args:
        origin: Where the string came from (e.g. ``Column.render() 'name'``).
        snippet: The offending string (only a prefix is kept for dedup).
        fix: Developer guidance included in the warning.
    """
    if not looks_like_html(snippet):
        return
    key = (origin, str(snippet)[:80])
    if key in _warned_html_strings:
        return
    _warned_html_strings.add(key)
    logger.warning(
        "renderer_returned_html_string origin=%r snippet=%r fix=%r",
        origin,
        str(snippet)[:120],
        fix,
    )


def _debug_components_enabled() -> bool:
    """Whether component debugging is on for this process.

    Cached because it is consulted per cell: a table of 50 rows by 8
    columns would otherwise rebuild the config 400 times per request.
    """
    global _debug_components_cache
    if _debug_components_cache is None:
        from lexigram.ui.config import UIConfig  # lazy: circular at import time

        try:
            _debug_components_cache = bool(UIConfig().debug_components)
        except Exception as e:  # noqa: BLE001
            logger.debug("ui_config_load_failed", error=str(e))
            _debug_components_cache = False
    return _debug_components_cache


def html_string_notice(value: Any, origin: str = "") -> Any:
    """Render an escaped HTML string so it reads as text, not broken markup.

    A renderer that returns an HTML *string* has its output escaped by the
    element layer, so the browser shows ``&lt;span&gt;...`` where a widget
    was intended. The escaping is correct -- strings are data -- but the
    result looks like corrupted output rather than a mistake in the code.

    This presents the value as what it actually is: literal text. The
    monospace treatment signals "not rendered markup" on its own, and when
    ``debug_components`` is enabled a short label names the origin so the
    developer can find the renderer.

    The label is gated on the debug flag rather than shown always because
    ``looks_like_html`` is a heuristic: values such as ``List<String>`` or
    ``Widget <Pro> Edition`` match it, and captioning genuine product data
    as a developer error in front of end users would be worse than the
    problem it reports.

    Args:
        value: The offending string, rendered escaped by the element layer.
        origin: Where the string came from, shown only in debug mode.

    Returns:
        An element wrapping ``value``.
    """
    code = el(
        "code",
        value,
        class_=(
            "font-mono text-xs break-all rounded bg-muted px-1 py-0.5 "
            "text-muted-foreground"
        ),
    )
    if not _debug_components_enabled():
        return code

    return el(
        "span",
        code,
        el(
            "span",
            "unrendered HTML string" + (f" from {origin}" if origin else ""),
            class_=(
                "ml-1.5 inline-flex items-center rounded border "
                "border-warning/30 bg-warning/10 px-1.5 py-0.5 text-[10px] "
                "font-medium uppercase tracking-wide text-warning"
            ),
        ),
        class_="inline-flex items-center gap-0.5 align-middle",
        title=(
            "This renderer returned an HTML string, which is escaped and "
            "shown as text. Return el(...) or wrap it in raw()/Markup."
        ),
    )

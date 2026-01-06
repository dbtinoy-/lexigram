"""Audit tests for HTMX and HTML attribute conversion in Element.__html__().

This test module verifies that the underscore-to-hyphen attribute conversion
in :class:`~lexigram.ui.core.base.Element` correctly handles:

- All standard HTMX 2.x ``hx_*`` → ``hx-*`` attribute mappings
- Boolean HTMX attributes (present/absent in output HTML)
- HTMX ``hx_on_*`` event handler shorthand (``hx_on_click`` → ``hx-on-click``)
- Python reserved-word escaping (``class_`` → ``class``, ``for_`` → ``for``)
- ``data-*`` and ``aria-*`` pass-through
- ``None`` and ``False`` attribute suppression
- Special button auto-type injection for HTMX-enabled buttons
"""

import pytest

from lexigram.ui.core.base import Element


class TestHtmxCoreAttributes:
    """Standard HTMX 2.x request attrs (hx_get, hx_post, etc.) → hx-*."""

    def test_hx_get(self) -> None:
        el = Element("div", hx_get="/api/items")
        assert 'hx-get="/api/items"' in el.__html__()

    def test_hx_post(self) -> None:
        el = Element("div", hx_post="/api/items")
        assert 'hx-post="/api/items"' in el.__html__()

    def test_hx_put(self) -> None:
        el = Element("div", hx_put="/api/items/1")
        assert 'hx-put="/api/items/1"' in el.__html__()

    def test_hx_patch(self) -> None:
        el = Element("div", hx_patch="/api/items/1")
        assert 'hx-patch="/api/items/1"' in el.__html__()

    def test_hx_delete(self) -> None:
        el = Element("div", hx_delete="/api/items/1")
        assert 'hx-delete="/api/items/1"' in el.__html__()


class TestHtmxTargetingAttributes:
    """Target, swap, and select attrs."""

    def test_hx_target(self) -> None:
        el = Element("div", hx_target="#results")
        assert 'hx-target="#results"' in el.__html__()

    def test_hx_swap(self) -> None:
        el = Element("div", hx_swap="innerHTML")
        assert 'hx-swap="innerHTML"' in el.__html__()

    def test_hx_swap_oob(self) -> None:
        el = Element("div", hx_swap_oob="true")
        assert 'hx-swap-oob="true"' in el.__html__()

    def test_hx_select(self) -> None:
        el = Element("div", hx_select="#content")
        assert 'hx-select="#content"' in el.__html__()

    def test_hx_select_oob(self) -> None:
        el = Element("div", hx_select_oob="#sidebar:#sidebar")
        assert 'hx-select-oob="#sidebar:#sidebar"' in el.__html__()


class TestHtmxTriggerAndBehaviourAttributes:
    """Trigger, push-url, history, indicator, and include attrs."""

    def test_hx_trigger(self) -> None:
        el = Element("div", hx_trigger="click")
        assert 'hx-trigger="click"' in el.__html__()

    def test_hx_trigger_delay(self) -> None:
        el = Element("input", hx_trigger="keyup delay:500ms")
        assert 'hx-trigger="keyup delay:500ms"' in el.__html__()

    def test_hx_push_url(self) -> None:
        el = Element("div", hx_push_url="true")
        assert 'hx-push-url="true"' in el.__html__()

    def test_hx_replace_url(self) -> None:
        el = Element("div", hx_replace_url="true")
        assert 'hx-replace-url="true"' in el.__html__()

    def test_hx_include(self) -> None:
        el = Element("div", hx_include="#form")
        assert 'hx-include="#form"' in el.__html__()

    def test_hx_indicator(self) -> None:
        el = Element("div", hx_indicator="#spinner")
        assert 'hx-indicator="#spinner"' in el.__html__()

    def test_hx_params(self) -> None:
        el = Element("div", hx_params="*")
        assert 'hx-params="*"' in el.__html__()

    def test_hx_vals(self) -> None:
        el = Element("div", hx_vals='{"key": "value"}')
        assert "hx-vals=" in el.__html__()

    def test_hx_headers(self) -> None:
        el = Element("div", hx_headers='{"X-CSRFToken": "abc"}')
        assert "hx-headers=" in el.__html__()

    def test_hx_encoding(self) -> None:
        el = Element("form", hx_encoding="multipart/form-data")
        assert 'hx-encoding="multipart/form-data"' in el.__html__()

    def test_hx_confirm(self) -> None:
        el = Element("button", hx_confirm="Are you sure?")
        assert 'hx-confirm="Are you sure?"' in el.__html__()

    def test_hx_disable(self) -> None:
        el = Element("div", hx_disable=True)
        html = el.__html__()
        assert "hx-disable" in html

    def test_hx_disabled_elt(self) -> None:
        el = Element("div", hx_disabled_elt="this")
        assert 'hx-disabled-elt="this"' in el.__html__()

    def test_hx_sync(self) -> None:
        el = Element("div", hx_sync="closest form:abort")
        assert 'hx-sync="closest form:abort"' in el.__html__()

    def test_hx_validate(self) -> None:
        el = Element("div", hx_validate=True)
        assert "hx-validate" in el.__html__()

    def test_hx_history(self) -> None:
        el = Element("div", hx_history="false")
        assert 'hx-history="false"' in el.__html__()

    def test_hx_history_elt(self) -> None:
        el = Element("div", hx_history_elt=True)
        assert "hx-history-elt" in el.__html__()

    def test_hx_preserve(self) -> None:
        el = Element("div", hx_preserve=True)
        assert "hx-preserve" in el.__html__()

    def test_hx_prompt(self) -> None:
        el = Element("div", hx_prompt="Enter a value:")
        assert 'hx-prompt="Enter a value:"' in el.__html__()

    def test_hx_request(self) -> None:
        el = Element("div", hx_request='{"timeout": 5000}')
        assert "hx-request=" in el.__html__()


class TestHtmxBoostAndLoadAttributes:
    """hx-boost and hx-ext."""

    def test_hx_boost_true(self) -> None:
        el = Element("div", hx_boost=True)
        html = el.__html__()
        assert "hx-boost" in html

    def test_hx_boost_string(self) -> None:
        el = Element("div", hx_boost="true")
        assert 'hx-boost="true"' in el.__html__()

    def test_hx_ext(self) -> None:
        el = Element("div", hx_ext="json-enc")
        assert 'hx-ext="json-enc"' in el.__html__()

    def test_hx_disinherit(self) -> None:
        el = Element("div", hx_disinherit="*")
        assert 'hx-disinherit="*"' in el.__html__()


class TestHtmxOnEventHandlers:
    """hx_on_* shorthand event handlers (HTMX 2.x hx-on:* / hx-on-* compat).

    The underscore→hyphen rule converts ``hx_on_click`` → ``hx-on-click``
    which is the correct shorthand form accepted by HTMX.
    """

    def test_hx_on_click(self) -> None:
        el = Element("button", hx_on_click="alert('hi')")
        html = el.__html__()
        assert "hx-on-click=" in html
        # Must NOT produce the raw Python name
        assert "hx_on_click" not in html

    def test_hx_on_htmx_before_request(self) -> None:
        el = Element("div", hx_on_htmx_before_request="doSomething()")
        html = el.__html__()
        assert "hx-on-htmx-before-request=" in html
        assert "hx_on_htmx_before_request" not in html

    def test_hx_on_htmx_after_request(self) -> None:
        el = Element("div", hx_on_htmx_after_request="doSomething()")
        html = el.__html__()
        assert "hx-on-htmx-after-request=" in html

    def test_hx_on_htmx_after_swap(self) -> None:
        el = Element("div", hx_on_htmx_after_swap="init()")
        html = el.__html__()
        assert "hx-on-htmx-after-swap=" in html


class TestBooleanAttributeSuppression:
    """None and False values must produce no attribute in the HTML output."""

    def test_none_value_suppressed(self) -> None:
        el = Element("div", hx_target=None)
        assert "hx-target" not in el.__html__()

    def test_false_value_suppressed(self) -> None:
        el = Element("div", hx_boost=False)
        assert "hx-boost" not in el.__html__()

    def test_true_value_is_bare_attribute(self) -> None:
        el = Element("div", hx_boost=True)
        html = el.__html__()
        assert "hx-boost" in html
        # Boolean True renders as bare attribute, not hx-boost="True"
        assert 'hx-boost="' not in html


class TestPythonReservedWordEscaping:
    """class_, for_, id_ trailing-underscore rule must not corrupt hx_ names."""

    def test_class_underscore_becomes_class(self) -> None:
        el = Element("div", class_="container")
        assert 'class="container"' in el.__html__()
        assert "class_" not in el.__html__()

    def test_for_underscore_becomes_for(self) -> None:
        el = Element("label", for_="email")
        assert 'for="email"' in el.__html__()
        assert "for_" not in el.__html__()

    def test_trailing_underscore_rule_does_not_affect_hx_attrs(self) -> None:
        """hx_get has underscore in the middle — must not strip trailing underscore."""
        el = Element("div", hx_get="/api")
        html = el.__html__()
        # Must produce hx-get, not hx-ge
        assert 'hx-get="/api"' in html

    def test_data_attribute_conversion(self) -> None:
        el = Element("div", data_user_id="42")
        assert 'data-user-id="42"' in el.__html__()

    def test_aria_label_conversion(self) -> None:
        el = Element("button", aria_label="Close dialog")
        assert 'aria-label="Close dialog"' in el.__html__()

    def test_aria_expanded_conversion(self) -> None:
        el = Element("button", aria_expanded="false")
        assert 'aria-expanded="false"' in el.__html__()

    def test_aria_controls_conversion(self) -> None:
        el = Element("button", aria_controls="menu")
        assert 'aria-controls="menu"' in el.__html__()


class TestButtonAutoType:
    """HTMX buttons get type='button' automatically to avoid accidental form submits."""

    def test_htmx_button_gets_type_button(self) -> None:
        el = Element("button", hx_post="/submit")
        assert 'type="button"' in el.__html__()

    def test_button_explicit_type_not_overridden(self) -> None:
        el = Element("button", type="submit", hx_post="/submit")
        assert 'type="submit"' in el.__html__()
        assert el.__html__().count("type=") == 1

    def test_non_htmx_button_has_no_auto_type(self) -> None:
        el = Element("button", id="plain")
        assert "type=" not in el.__html__()


class TestHtmlEscaping:
    """Attribute values must be HTML-escaped to prevent XSS."""

    def test_attribute_value_is_html_escaped(self) -> None:
        el = Element("div", hx_confirm='<script>alert("xss")</script>')
        html = el.__html__()
        assert "<script>" not in html
        assert "&lt;script&gt;" in html

    def test_double_quotes_in_value_are_escaped(self) -> None:
        el = Element("div", title='say "hello"')
        html = el.__html__()
        assert '"hello"' not in html
        assert "&quot;hello&quot;" in html

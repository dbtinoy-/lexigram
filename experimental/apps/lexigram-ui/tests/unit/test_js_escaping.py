"""Values crossing into inline JavaScript must not become code.

HTML escaping does not protect a JS context. A value interpolated into a JS
string literal is injectable by a bare quote, which needs no HTML
metacharacter, so ``html.escape`` neither prevents the attack nor survives
the round trip -- inside a script the JS parser sees ``&#x27;``, not a
quote. These tests cover the encoder and the components that were shipping
this bug.

The assertions deliberately parse the emitted literal rather than grepping
for a payload substring: an escaped payload still *contains* the attack
text, so a substring check passes for the wrong reason.
"""

from __future__ import annotations

import html
import json

import pytest

from lexigram.ui import render_to_string
from lexigram.ui.core.js import js_json, js_string

#: Payloads that break out of a single-quoted JS string, a double-quoted
#: one, the enclosing <script> element, or a JS line.
BREAKOUT_PAYLOADS = [
    "');alert(document.cookie);('",
    '");alert(1);("',
    "</script><img src=x onerror=alert(1)>",
    "\u2028alert(1)",
    "\u2029alert(1)",
    "\\'); alert(1); //",
    "\\\\';alert(1);//",
]


def _decoder() -> json.JSONDecoder:
    return json.JSONDecoder()


def _literal_at(rendered: str, marker: str) -> str:
    """Return the JS literal that follows ``marker`` in ``rendered``.

    Uses ``raw_decode`` so the literal's own bounds are found by a real
    parser. Splitting on a delimiter would truncate any payload that
    contains that delimiter -- which is exactly what these payloads do.
    """
    start = rendered.index(marker) + len(marker)
    value, _ = _decoder().raw_decode(rendered[start:])
    return value


class TestJsString:
    def test_produces_its_own_quotes(self) -> None:
        """Callers must not add quotes; doing so reintroduces the bug."""
        assert js_string("x") == '"x"'

    @pytest.mark.parametrize("payload", BREAKOUT_PAYLOADS)
    def test_payload_round_trips_exactly(self, payload: str) -> None:
        """The literal must decode back to the input: no escape, no loss."""
        assert json.loads(js_string(payload)) == payload

    def test_script_close_cannot_end_the_block(self) -> None:
        """The HTML tokenizer ignores JS quoting, so a literal </script>
        inside a string still closes the element."""
        assert "</script>" not in js_string("</script>")
        assert "\\u003c/script\\u003e" in js_string("</script>")

    def test_html_breakout_characters_are_escaped(self) -> None:
        literal = js_string("<&>")

        assert "<" not in literal
        assert ">" not in literal
        assert "&" not in literal

    def test_js_line_terminators_are_escaped(self) -> None:
        """U+2028/9 are valid in JSON but terminate a line in JavaScript."""
        assert "\u2028" not in js_string("\u2028")
        assert "\u2029" not in js_string("\u2029")

    def test_none_becomes_empty_string_not_null(self) -> None:
        """Callers use this for text and URLs; a null would change type."""
        assert js_string(None) == '""'

    def test_non_strings_are_stringified(self) -> None:
        assert json.loads(js_string(42)) == "42"


class TestJsJson:
    def test_preserves_structure(self) -> None:
        assert json.loads(js_json({"a": [1, 2]})) == {"a": [1, 2]}

    def test_escapes_breakout_inside_values(self) -> None:
        literal = js_json({"k": "</script>"})

        assert "</script>" not in literal
        assert json.loads(literal.replace("\\u003c", "<").replace("\\u003e", ">")) == {
            "k": "</script>"
        }

    def test_raises_on_unserialisable(self) -> None:
        """Falling back to str() would emit a Python repr into a script."""
        with pytest.raises(TypeError):
            js_json(object())


class TestNotificationBell:
    """URLs reach this component from configuration and are placed in JS."""

    @pytest.mark.parametrize("payload", BREAKOUT_PAYLOADS)
    def test_sse_url_cannot_escape_its_literal(self, payload: str) -> None:
        from lexigram.ui.organisms.notification_bell import NotificationBell

        rendered = render_to_string(NotificationBell(sse_url=payload))

        assert _literal_at(rendered, "new EventSource(") == payload

    def test_script_block_is_not_closed_early(self) -> None:
        from lexigram.ui.organisms.notification_bell import NotificationBell

        rendered = render_to_string(
            NotificationBell(sse_url="</script><img src=x onerror=alert(1)>")
        )
        body = rendered.split("<script>")[1].split("</script>")[0]

        assert "<img" not in body

    def test_normal_url_is_unchanged(self) -> None:
        from lexigram.ui.organisms.notification_bell import NotificationBell

        rendered = render_to_string(NotificationBell(sse_url="/admin/_sse/widgets"))

        assert _literal_at(rendered, "new EventSource(") == "/admin/_sse/widgets"

    def test_max_display_is_numeric(self) -> None:
        """It is emitted bare, outside any quotes, so it must be an int."""
        from lexigram.ui.organisms.notification_bell import NotificationBell

        rendered = render_to_string(NotificationBell(max_display=7))

        assert "notifications.length > 7" in rendered


class TestTaskProgress:
    """``on_complete`` was concatenated in as executable code."""

    def _script(self, **kwargs: object) -> str:
        from lexigram.ui.organisms.task_progress import TaskProgress

        # The script here is carried in an Alpine x-data attribute, so the
        # browser HTML-decodes it before Alpine evaluates it as JavaScript.
        # Decode here too, or the assertion inspects the wrong string.
        return html.unescape(render_to_string(TaskProgress(**kwargs)))  # type: ignore[arg-type]

    def _event_source_arg(self, rendered: str) -> str:
        """Return the decoded argument of ``new EventSource(...)``.

        Unlike the notification bell, this literal is embedded in a larger
        JS source fragment, so it can legitimately contain JS escapes such
        as ``\\'`` that are not valid JSON. Scan for the closing quote
        honouring backslash escapes, then interpret them as JS would.
        """
        start = rendered.index("new EventSource(") + len("new EventSource(")
        assert rendered[start] == '"', "argument must be a quoted literal"

        index = start + 1
        chars: list[str] = []
        while rendered[index] != '"':
            if rendered[index] != "\\":
                chars.append(rendered[index])
                index += 1
                continue

            escape = rendered[index + 1]
            if escape == "u":
                chars.append(chr(int(rendered[index + 2 : index + 6], 16)))
                index += 6
            else:
                # \' is valid JS but not valid JSON; the rest are shared.
                chars.append("'" if escape == "'" else json.loads(f'"\\{escape}"'))
                index += 2
        return "".join(chars)

    @pytest.mark.parametrize("payload", BREAKOUT_PAYLOADS)
    def test_stream_url_cannot_escape_its_literal(self, payload: str) -> None:
        rendered = self._script(task_id="t", stream_url=payload)

        assert self._event_source_arg(rendered) == payload

    def test_task_id_cannot_escape_the_derived_url(self) -> None:
        rendered = self._script(task_id="');alert(1);//")

        assert self._event_source_arg(rendered) == (
            "/admin/progress/');alert(1);///stream"
        )

    @pytest.mark.parametrize(
        "callback",
        [
            "alert(document.cookie)",
            "x;alert(1)",
            "javascript:alert(1)",
            "a()||b()",
            "'-alert(1)-'",
        ],
    )
    def test_arbitrary_code_is_rejected(self, callback: str) -> None:
        """There is no encoding that makes attacker code safe to execute, so
        anything that is not a plain identifier path is dropped."""
        rendered = self._script(task_id="t", on_complete=callback)

        assert callback not in rendered

    @pytest.mark.parametrize("target", ["//evil.test", "https://evil.test"])
    def test_offsite_redirects_are_rejected(self, target: str) -> None:
        rendered = self._script(task_id="t", on_complete=target)

        assert "evil.test" not in rendered

    def test_identifier_callback_still_runs(self) -> None:
        rendered = self._script(task_id="t", on_complete="app.onDone")

        assert "app.onDone();" in rendered

    def test_local_redirect_still_works(self) -> None:
        rendered = self._script(task_id="t", on_complete="/admin/done")

        assert 'window.location.href = "/admin/done";' in rendered

    def test_redirect_target_is_an_encoded_literal(self) -> None:
        rendered = self._script(task_id="t", on_complete='/admin/"+alert(1)+"')

        assert "+alert(1)+" not in rendered.replace('\\"+alert(1)+\\"', "")


class TestInfolistIcon:
    """``icon`` was rendered as raw markup."""

    def _render(self, icon: str) -> str:
        from lexigram.ui.molecules.infolist import InfolistEntry, InfolistWidget

        entry = InfolistEntry(name="n", label="L", value="v", icon=icon)
        return render_to_string(InfolistWidget(entries=[entry]).render())

    def test_markup_is_not_injected(self) -> None:
        rendered = self._render("<img src=x onerror=alert(1)>")

        assert "<img" not in rendered
        assert "onerror" not in rendered

    def test_script_is_not_injected(self) -> None:
        rendered = self._render("<script>alert(1)</script>")

        assert "<script>" not in rendered

    def test_known_icon_still_renders(self) -> None:
        """The fix must not silently blank out legitimate icons."""
        assert "<svg" in self._render("users")

    def test_unknown_icon_renders_nothing_dangerous(self) -> None:
        rendered = self._render("definitely-not-an-icon")

        assert "<img" not in rendered
        assert "<script" not in rendered


class TestChartRenderers:
    """Chart labels, titles and ids are caller data placed in a script."""

    def _renderers(self) -> list[object]:
        from lexigram.admin.services.charts import ChartJSRenderer, PlotlyRenderer

        return [ChartJSRenderer(), PlotlyRenderer()]

    def _render(self, renderer: object, **options: object) -> str:
        from lexigram.admin.services.charts import ChartData, ChartType

        data = ChartData(
            labels=options.pop("labels", ["Jan"]),  # type: ignore[arg-type]
            datasets=[{"label": options.pop("series", "Sales"), "data": [1]}],
            title=options.pop("title", "T"),  # type: ignore[arg-type]
        )
        return renderer.render(ChartType.BAR, data, **options)  # type: ignore[attr-defined]

    @pytest.mark.parametrize("field", ["labels", "series", "title"])
    def test_data_cannot_close_the_script_block(self, field: str) -> None:
        payload = "</script><img src=x onerror=alert(1)>"
        value = [payload] if field == "labels" else payload

        for renderer in self._renderers():
            rendered = self._render(renderer, **{field: value})

            assert "<img" not in rendered
            assert rendered.count("</script>") == rendered.count("<script")

    def test_chart_id_cannot_break_out_of_the_attribute(self) -> None:
        for renderer in self._renderers():
            rendered = self._render(renderer, id='c"><img src=x onerror=alert(1)>')

            assert "<img" not in rendered

    @pytest.mark.parametrize("payload", BREAKOUT_PAYLOADS)
    def test_chart_id_cannot_break_out_of_the_js_literal(self, payload: str) -> None:
        """A quote in the id must stay data. Asserting the payload text is
        absent would be wrong -- it may legitimately appear verbatim inside
        a double-quoted literal -- so decode the literal and compare."""
        for renderer, marker in (
            (self._renderers()[0], "getElementById("),
            (self._renderers()[1], "Plotly.newPlot("),
        ):
            rendered = self._render(renderer, id=payload)

            assert _literal_at(rendered, marker) == payload

    def test_dimensions_cannot_break_out_of_the_style_attribute(self) -> None:
        for renderer in self._renderers():
            rendered = self._render(renderer, width='"><img src=x onerror=alert(1)>')

            assert "<img" not in rendered

    def test_legitimate_chart_still_renders(self) -> None:
        """Encoding must not break the normal path."""
        from lexigram.admin.services.charts import ChartJSRenderer, PlotlyRenderer

        chartjs = self._render(ChartJSRenderer(), labels=["Jan", "Feb"], id="sales")
        assert 'id="sales"' in chartjs
        assert "new Chart(ctx," in chartjs
        assert "Jan" in chartjs

        plotly = self._render(PlotlyRenderer(), id="sales")
        assert 'id="sales"' in plotly
        assert 'Plotly.newPlot("sales"' in plotly

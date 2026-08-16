"""Literal escaping and re-parse safety for Meilisearch/Typesense filters.

Regression suite closing the F1/F2 filter-expression injection findings:
caller-supplied values (free text — dates, names, paths, user input)
must round-trip inside a ``"``-delimited literal in both dialects, so
they can never terminate the literal and rewrite the scoped query's
grammar (filter bypass, cross-tenant disclosure, DoS via bad grammar).
"""

from __future__ import annotations

import pytest

from lexigram.search.backends.filters import (
    render_meilisearch,
    render_typesense,
)

HOSTILE_PAYLOADS: tuple[str, ...] = (
    'a" OR tenant_id != "" OR x="',
    '");) || (tenant_id:!=',
    "C:\\temp\\",
    "line1\nline2",
    "",
    'say "hi" \\ path',
)

BENIGN_QUOTED_VALUES: tuple[str, ...] = (
    "2026-08-17",
    "O'Brien",
    'say "hi"',
    "C:\\temp\\report.pdf",
    "plain value",
)


def _value_region(rendered: str) -> str:
    """Extract the literal's inner content from an equality render.

    Only equality renders are used here, so the value region is the text
    between the opening ``"`` and the final closing ``"``. An unescaped
    ``"`` inside the region means the payload escaped the literal — the
    exact failure mode being closed.
    """
    opening = rendered.index('"') + 1
    closing = rendered.rindex('"')
    assert opening <= closing
    return rendered[opening:closing]


def _reparse_lossless(region: str, payload: str) -> bool:
    """Un-escape the region with the documented backslash rule.

    Returns ``False`` on any unescaped quote, dangling backslash, or a
    re-parse that does not reproduce the original payload.
    """
    out: list[str] = []
    i = 0
    while i < len(region):
        char = region[i]
        if char == "\\":
            if i + 1 >= len(region):
                return False
            out.append(region[i + 1])
            i += 2
            continue
        if char == '"':
            return False
        out.append(char)
        i += 1
    return "".join(out) == payload


class TestBenignNoChangeGuard:
    """Benign values render exactly as before (Meili) or per the quoted flip (Typesense)."""

    def test_meili_equality_unchanged(self) -> None:
        assert render_meilisearch({"status": "active"}) == 'status = "active"'

    def test_typesense_equality_quoted(self) -> None:
        assert render_typesense({"status": "active"}) == 'status:"active"'

    def test_numbers_unquoted_in_both_dialects(self) -> None:
        assert render_meilisearch({"score": 80}) == "score = 80"
        assert render_typesense({"score": 80}) == "score:80"

    def test_bools_unquoted_in_both_dialects(self) -> None:
        assert render_meilisearch({"ok": True}) == "ok = true"
        assert render_typesense({"ok": True}) == "ok:true"
        assert render_meilisearch({"ok": False}) == "ok = false"
        assert render_typesense({"ok": False}) == "ok:false"

    def test_date_literal_stays_inside_one_quoted_value(self) -> None:
        assert render_meilisearch({"created": "2026-08-17"}) == 'created = "2026-08-17"'
        assert render_typesense({"created": "2026-08-17"}) == 'created:"2026-08-17"'

    def test_apostrophe_is_not_escaped(self) -> None:
        assert render_meilisearch({"name": "O'Brien"}) == 'name = "O\'Brien"'
        assert render_typesense({"name": "O'Brien"}) == 'name:"O\'Brien"'

    def test_embedded_quotes_escaped(self) -> None:
        assert render_meilisearch({"name": 'say "hi"'}) == 'name = "say \\"hi\\""'
        assert render_typesense({"name": 'say "hi"'}) == 'name:"say \\"hi\\""'


class TestInNinMemberEscaping:
    """``in``/``nin`` members route through the same escaping helpers."""

    def test_typesense_in_members_quoted(self) -> None:
        assert render_typesense({"tags": {"in": ["x", "y"]}}) == 'tags:["x","y"]'

    def test_typesense_nin_members_quoted(self) -> None:
        assert render_typesense({"tags": {"nin": ["x", "y"]}}) == '!(tags:["x","y"])'

    def test_meili_in_members_escaped(self) -> None:
        assert render_meilisearch({"tags": {"in": ['a"b', "c\\d"]}}) == (
            'tags IN ["a\\"b", "c\\\\d"]'
        )

    def test_typesense_in_members_escaped(self) -> None:
        assert render_typesense({"tags": {"in": ['a"b', "c\\d"]}}) == (
            'tags:["a\\"b","c\\\\d"]'
        )


class TestExactEscapedOutputs:
    """Headline hostile payloads produce exact, locked byte-for-byte output."""

    def test_meili_quote_injection_escaped_exactly(self) -> None:
        rendered = render_meilisearch({"tenant_id": 'a" OR tenant_id != "" OR x="'})
        assert rendered == 'tenant_id = "a\\" OR tenant_id != \\"\\" OR x=\\""'

    def test_typesense_quote_injection_escaped_exactly(self) -> None:
        rendered = render_typesense({"tenant_id": 'a" OR tenant_id != "" OR x="'})
        assert rendered == 'tenant_id:"a\\" OR tenant_id != \\"\\" OR x=\\""'

    def test_meili_paren_injection_escaped_exactly(self) -> None:
        rendered = render_meilisearch({"tenant_id": '");) || (tenant_id:!='})
        assert rendered == 'tenant_id = "\\");) || (tenant_id:!="'

    def test_typesense_paren_injection_escaped_exactly(self) -> None:
        rendered = render_typesense({"tenant_id": '");) || (tenant_id:!='})
        assert rendered == 'tenant_id:"\\");) || (tenant_id:!="'


class TestLiteralRoundTrip:
    """Hostile (and quiet) payloads re-parse losslessly — grammar cannot be rewritten."""

    @pytest.mark.parametrize("payload", HOSTILE_PAYLOADS)
    def test_meili_round_trip(self, payload: str) -> None:
        rendered = render_meilisearch({"tenant_id": payload})
        assert _reparse_lossless(_value_region(rendered), payload)

    @pytest.mark.parametrize("payload", HOSTILE_PAYLOADS)
    def test_typesense_round_trip(self, payload: str) -> None:
        rendered = render_typesense({"tenant_id": payload})
        assert _reparse_lossless(_value_region(rendered), payload)

    @pytest.mark.parametrize("payload", BENIGN_QUOTED_VALUES)
    def test_benign_values_round_trip_single_escaped(self, payload: str) -> None:
        assert _reparse_lossless(_value_region(render_meilisearch({"v": payload})), payload)
        assert _reparse_lossless(_value_region(render_typesense({"v": payload})), payload)

"""Helpers for embedding Python values inside inline ``<script>`` blocks.

HTML escaping does not make a value safe inside JavaScript. A component that
interpolates into a JS string literal::

    raw(f"new EventSource('{url}');")

is injectable by a value containing a single quote, and the payload needs no
HTML metacharacters at all, so passing it through ``Element`` attribute
escaping or ``html.escape`` does not help. The reverse is also true: a value
escaped for HTML and then placed in a script is silently corrupted, because
the JS parser sees ``&#x27;`` rather than a quote.

``js_string`` produces a complete, quoted JS string literal that is safe in
both the JavaScript grammar and the surrounding HTML parser. Use it wherever
a value crosses into script content:

    el("script", raw(f"new EventSource({js_string(url)});"))

Note the absent quotes around the placeholder -- ``js_string`` supplies its
own. Wrapping it in quotes again would reintroduce the bug it prevents.
"""

from __future__ import annotations

# Deliberately stdlib json rather than lexigram.serialization: the project
# encoder coerces unserialisable objects into their Python repr, which in a
# security helper means quietly emitting internals into a script instead of
# failing. Strict encoding matters more than speed for these small payloads.
import json  # noqa: TID251
from typing import Any

#: Characters that terminate or reopen HTML parsing from inside a script
#: element. The HTML tokenizer does not respect JavaScript string quoting,
#: so a literal ``</script>`` inside a JS string still closes the block and
#: everything after it is parsed as markup.
_HTML_BREAKOUT = {
    "<": "\\u003c",
    ">": "\\u003e",
    "&": "\\u0026",
}

#: Valid in JSON but line terminators in JavaScript, so leaving them raw
#: produces a syntax error (or, historically, a parser split).
_JS_LINE_TERMINATORS = {
    "\u2028": "\\u2028",
    "\u2029": "\\u2029",
}


def js_string(value: Any) -> str:
    """Return ``value`` as a quoted JavaScript string literal.

    The result includes its own surrounding quotes and is safe to embed
    directly in an inline script. ``None`` becomes the JS string ``""``
    rather than ``null``, because callers use this for text and URLs where a
    missing value should not change the expression's type.

    Args:
        value: Any value; non-strings are rendered via ``str()`` first so a
            path object or integer id can be embedded without ceremony.

    Returns:
        A JS string literal, quotes included, with HTML-breakout characters
        and JS line terminators escaped as ``\\uXXXX`` sequences.

    Example:
        >>> js_string("a'b")
        '"a\\'b"'
        >>> js_string("</script>")
        '"\\\\u003c/script\\\\u003e"'
    """
    text = "" if value is None else str(value)

    # json.dumps handles quotes, backslashes, control characters, and
    # non-ASCII correctly for the JS grammar; JS string syntax is a superset
    # of JSON string syntax. It does not know about HTML, so the breakout
    # characters are neutralised afterwards.
    literal = json.dumps(text)

    for char, replacement in _HTML_BREAKOUT.items():
        literal = literal.replace(char, replacement)
    for char, replacement in _JS_LINE_TERMINATORS.items():
        literal = literal.replace(char, replacement)

    return literal


def js_json(value: Any) -> str:
    """Return ``value`` as a JS literal for structured data.

    Same guarantees as :func:`js_string`, but preserves the value's JSON
    shape so lists and mappings arrive as arrays and objects rather than as
    a string. Use it for config blobs handed to a script.

    Raises:
        TypeError: If ``value`` is not JSON-serialisable. Failing loudly is
            deliberate -- falling back to ``str()`` would embed a Python
            ``repr`` that is not valid JavaScript.
    """
    literal = json.dumps(value)

    for char, replacement in _HTML_BREAKOUT.items():
        literal = literal.replace(char, replacement)
    for char, replacement in _JS_LINE_TERMINATORS.items():
        literal = literal.replace(char, replacement)

    return literal


__all__ = ["js_json", "js_string"]

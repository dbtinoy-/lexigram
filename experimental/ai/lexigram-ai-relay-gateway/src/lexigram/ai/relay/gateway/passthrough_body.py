"""Passthrough request bodies and multipart field rewriting.

One forwarded gateway request body is a :class:`RelayPassthroughBody`:
either a decoded JSON object (content type ``application/json``) or raw
bytes with their content type (``multipart/form-data`` and friends).
The multipart helpers rewrite a single named form field in a raw body
without parsing it, used by the passthrough service to substitute the
outbound model alias.
"""

from __future__ import annotations

from collections.abc import Iterator, Mapping
from dataclasses import dataclass

from lexigram.contracts.ai.relay import JsonValue

__all__ = [
    "RelayPassthroughBody",
    "rewrite_multipart_form_field",
]

_JSON_CONTENT_TYPE = "application/json"
_FORM_FIELD_HEADER_MARKER = b'name="'
_FORM_FIELD_HEADER_SUFFIX = b'"'
"""Multipart ``Content-Disposition`` attribute delimiters used by the field rewrite."""


@dataclass(frozen=True, slots=True)
class RelayPassthroughBody(Mapping[str, JsonValue]):
    """One forwarded gateway request body: decoded JSON or raw bytes.

    The two constructors are the entire surface: :meth:`json` wraps a
    decoded JSON object (content type ``application/json``) and
    :meth:`raw` wraps arbitrary bytes with their content type, so
    ``multipart/form-data`` requests travel through the same
    ``RelayGatewayRequest.payload`` field as JSON bodies.  The mapping
    facade (``__getitem__``/``__iter__``/``__len__``) delegates to the
    JSON dict for ``json`` bodies and raises ``TypeError`` for raw
    bodies — the passthrough pipeline branches on whether ``data`` is a
    mapping and never treats raw content as JSON.

    Attributes:
        data: The decoded JSON object for ``json`` bodies, or the raw
            body bytes for ``raw`` bodies.
        content_type: Outbound content type header value; ``json``
            bodies always carry ``application/json``.
    """

    data: Mapping[str, JsonValue] | bytes
    content_type: str

    @classmethod
    def json(cls, payload: Mapping[str, JsonValue]) -> RelayPassthroughBody:
        """Wrap a decoded JSON object request body.

        Args:
            payload: The decoded JSON object to forward.

        Returns:
            A JSON body carrying ``application/json`` as its content
            type; the object is shallow-copied so later mutation of the
            source never leaks into the frozen body.
        """
        return cls(dict(payload), _JSON_CONTENT_TYPE)

    @classmethod
    def raw(cls, data: bytes, content_type: str) -> RelayPassthroughBody:
        """Wrap a raw (e.g. ``multipart/form-data``) request body.

        Args:
            data: The raw body bytes to forward verbatim.
            content_type: The body's content type header (boundary
                parameter included for multipart bodies).

        Returns:
            A raw body carrying *content_type* unchanged.
        """
        return cls(data, content_type)

    def __getitem__(self, key: str) -> JsonValue:
        """Return one JSON field for ``json`` bodies.

        Raises:
            TypeError: If the body is raw bytes, which are not JSON.
        """
        data = self.data
        if not isinstance(data, Mapping):
            raise TypeError("raw passthrough bodies are not JSON mappings")
        return data[key]

    def __iter__(self) -> Iterator[str]:
        """Iterate the JSON field names for ``json`` bodies.

        Raises:
            TypeError: If the body is raw bytes, which are not JSON.
        """
        data = self.data
        if not isinstance(data, Mapping):
            raise TypeError("raw passthrough bodies are not JSON mappings")
        return iter(data)

    def __len__(self) -> int:
        """Return the JSON field count for ``json`` bodies.

        Raises:
            TypeError: If the body is raw bytes, which are not JSON.
        """
        data = self.data
        if not isinstance(data, Mapping):
            raise TypeError("raw passthrough bodies are not JSON mappings")
        return len(data)


def rewrite_multipart_form_field(
    body: bytes,
    boundary: str,
    field: str,
    value: str,
) -> bytes:
    """Rewrite one named form field's value in a multipart body.

    Narrow boundary-aware rewrite (not a general multipart parser): the
    body is split on the ``--<boundary>`` framing marker and the first
    part whose ``Content-Disposition`` header carries
    ``name="<field>"`` has its value content swapped in place; every
    other byte — headers, other parts, the closing marker — is left
    untouched.  A body without the field (or without the boundary
    marker) is returned unchanged; that is not an error, some
    passthrough endpoints resolve the model from the URL path or a
    channel default instead of a body field.

    Args:
        body: The raw ``multipart/form-data`` body bytes.
        boundary: The boundary token from the content-type header.
        field: The form field name to rewrite (e.g. ``"model"``).
        value: The replacement field value.

    Returns:
        The body with the named field's value replaced, or the body
        unchanged when the field is absent.
    """
    marker = b"--" + boundary.encode("utf-8")
    target = (
        _FORM_FIELD_HEADER_MARKER + field.encode("utf-8") + _FORM_FIELD_HEADER_SUFFIX
    )
    replacement = value.encode("utf-8")
    segments = body.split(marker)
    if len(segments) < 2:
        return body
    for index in range(1, len(segments) - 1):
        part = segments[index]
        separator = part.find(b"\r\n\r\n")
        if separator < 0:
            continue
        headers = part[2:separator].lower()
        if target not in headers:
            continue
        value_end = len(part) - 2 if part.endswith(b"\r\n") else len(part)
        segments[index] = part[: separator + 4] + replacement + part[value_end:]
        return marker.join(segments)
    return body


def _as_relay_body(payload: Mapping[str, JsonValue]) -> RelayPassthroughBody:
    """Normalize a gateway request payload into a relay passthrough body.

    Bodies already carrying the relay carrier pass through unchanged;
    plain JSON mappings (legacy callers) are wrapped as JSON bodies.

    Args:
        payload: The ``RelayGatewayRequest.payload`` value.

    Returns:
        The payload as a :class:`RelayPassthroughBody`.
    """
    if isinstance(payload, RelayPassthroughBody):
        return payload
    return RelayPassthroughBody.json(dict(payload))


def _multipart_boundary(content_type: str) -> str | None:
    """Extract the ``boundary`` parameter from a content-type header.

    Args:
        content_type: The raw content-type header value.

    Returns:
        The boundary token without surrounding quotes, or ``None`` when
        the header carries no boundary parameter.
    """
    for parameter in content_type.split(";"):
        key, separator, raw_value = parameter.strip().partition("=")
        if separator and key.lower() == "boundary":
            return raw_value.strip().strip('"')
    return None


def _is_json_content_type(content_type: str) -> bool:
    """Tell whether a content-type value denotes JSON.

    Args:
        content_type: A content-type header value.

    Returns:
        ``True`` for the exact ``application/json`` media type and for
        any ``*+json`` suffix variant; ``False`` otherwise.
    """
    media_type = content_type.partition(";")[0].strip().lower()
    return media_type == _JSON_CONTENT_TYPE or media_type.endswith("+json")

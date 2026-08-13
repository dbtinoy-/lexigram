"""Pure data-URI decoding and URL media resolution for relay conversion.

The engine is synchronous and side-effect free.  It never performs
network I/O: data URIs are decoded locally, and URL media is resolved
through the host-supplied resolver on :class:`ConversionContext`.
"""

from __future__ import annotations

import base64
import binascii

from lexigram.ai.relay.context import ConversionContext
from lexigram.ai.relay.errors import media_resolution_required, serialization_error
from lexigram.contracts.ai.exceptions import RelayError
from lexigram.contracts.ai.relay.types import RelayFormat, RelayLoss
from lexigram.contracts.core.result import Err, Ok, Result

__all__ = ["decode_data_uri", "resolve_media"]

_DATA_URI_PREFIX = "data:"
_BASE64_MARKER = ";base64,"


def decode_data_uri(uri: str) -> Result[tuple[str, str], RelayError]:
    """Decode a base64 data URI into ``(media_type, data)``.

    Supports ``data:<media_type>;base64,<data>`` payloads.  The returned
    data is exactly the raw base64 text (no ``data:`` prefix), ready for
    protocols that consume inline base64 (Claude ``image_source.data``,
    Gemini ``inlineData.data``).

    Args:
        uri: A base64 data URI.

    Returns:
        ``Ok((media_type, data))`` on success, or ``Err(RelayError)``
        with code ``serialization_error`` when the URI is malformed,
        empty, or carries invalid base64.
    """
    if not uri.startswith(_DATA_URI_PREFIX):
        return Err(serialization_error("expected a data URI"))
    rest = uri[len(_DATA_URI_PREFIX) :]
    marker = rest.find(_BASE64_MARKER)
    if marker < 0:
        return Err(serialization_error("data URI must be base64 encoded"))
    media_type = rest[:marker]
    if not media_type:
        return Err(serialization_error("data URI media type is empty"))
    data = rest[marker + len(_BASE64_MARKER) :]
    if not data:
        return Err(serialization_error("data URI payload is empty"))
    try:
        base64.b64decode(data, validate=True)
    except (binascii.Error, ValueError):
        return Err(serialization_error("data URI payload is not valid base64"))
    return Ok((media_type, data))


def resolve_media(
    uri: str,
    context: ConversionContext,
    *,
    field: str,
    target: RelayFormat,
    lossy: bool = False,
) -> Result[tuple[str, str] | None, RelayError]:
    """Convert media content into ``(media_type, base64_data)``.

    Data URIs decode locally and never touch the resolver.  URL content
    is delegated to the context resolver; when no resolver exists the
    call fails with ``media_resolution_required`` unless *lossy* is set,
    in which case a ``media_unresolved_dropped`` loss is recorded and
    ``Ok(None)`` is returned.

    Args:
        uri: A data URI or URL that requires conversion.
        context: Per-conversion context holding the resolver and the loss
            sink.
        field: Source wire JSON field the content came from, carried into
            errors and losses.
        target: Target wire format, used when recording losses.
        lossy: When ``True``, unresolvable URL content degrades to a
            recorded loss instead of a hard error.

    Returns:
        ``Ok((media_type, data))``, ``Ok(None)`` for a lossy drop, or
        ``Err(RelayError)`` with the source field preserved.
    """
    if uri.startswith(_DATA_URI_PREFIX):
        decoded = decode_data_uri(uri)
        if decoded.is_err():
            return Err(_with_field(decoded.unwrap_err(), field))
        return Ok(decoded.unwrap())
    resolver = context.media_resolver
    if resolver is None:
        if lossy:
            context.losses.append(
                RelayLoss(
                    field=field,
                    target=target,
                    reason="media_unresolved_dropped",
                    severity="warning",
                )
            )
            return Ok(None)
        return Err(media_resolution_required(f"{field}: {uri}"))
    result = resolver.resolve(uri)
    if result.is_err():
        return Err(_with_field(result.unwrap_err(), field))
    return Ok(result.unwrap())


def _with_field(error: RelayError, field: str) -> RelayError:
    """Prefix a resolver error detail with the source JSON field."""
    return RelayError(f"{field}: {error}", code=error.code)

"""Stable ``RelayError`` factories for the relay conversion engine.

Mappers and the engine construct errors through these factories so every
failure carries one stable machine-readable code from
:class:`lexigram.contracts.ai.exceptions.RelayErrorCode`.  Callers branch
on ``error.code``, never on message text.
"""

from __future__ import annotations

from lexigram.contracts.ai.exceptions import RelayError, RelayErrorCode

__all__ = [
    "duplicate_registration",
    "malformed_payload",
    "media_resolution_required",
    "missing_required_option",
    "serialization_error",
    "stream_already_finalized",
    "stream_state_invalid",
    "translate",
    "unsupported_feature",
    "unsupported_format",
    "unsupported_route",
]


def malformed_payload(detail: str) -> RelayError:
    """The wire payload did not match the expected shape.

    Args:
        detail: Human-readable description of the malformed field.

    Returns:
        A ``RelayError`` with code ``malformed_payload``.
    """
    return RelayError(detail, code=RelayErrorCode.MALFORMED_PAYLOAD)


def missing_required_option(detail: str) -> RelayError:
    """A required field or host option is absent.

    Args:
        detail: Which required option is missing.

    Returns:
        A ``RelayError`` with code ``missing_required_option``.
    """
    return RelayError(detail, code=RelayErrorCode.MISSING_REQUIRED_OPTION)


def unsupported_feature(detail: str) -> RelayError:
    """The source feature cannot be converted to the target.

    Args:
        detail: The feature that could not be converted.

    Returns:
        A ``RelayError`` with code ``unsupported_feature``.
    """
    return RelayError(detail, code=RelayErrorCode.UNSUPPORTED_FEATURE)


def unsupported_format(detail: str) -> RelayError:
    """The payload does not belong to this mapper's wire format.

    Args:
        detail: The expected and actual payload shapes.

    Returns:
        A ``RelayError`` with code ``unsupported_format``.
    """
    return RelayError(detail, code=RelayErrorCode.UNSUPPORTED_FORMAT)


def unsupported_route(detail: str) -> RelayError:
    """No mapper exists for the requested source/target route.

    Args:
        detail: The route that cannot be converted.

    Returns:
        A ``RelayError`` with code ``unsupported_route``.
    """
    return RelayError(detail, code=RelayErrorCode.UNSUPPORTED_ROUTE)


def duplicate_registration(detail: str) -> RelayError:
    """A mapper was registered twice for one wire format.

    Args:
        detail: The format that was registered twice.

    Returns:
        A ``RelayError`` with code ``duplicate_registration``.
    """
    return RelayError(detail, code=RelayErrorCode.DUPLICATE_REGISTRATION)


def media_resolution_required(detail: str) -> RelayError:
    """URL media requires a resolver the host did not supply.

    Args:
        detail: The media URL that cannot be resolved.

    Returns:
        A ``RelayError`` with code ``media_resolution_required``.
    """
    return RelayError(detail, code=RelayErrorCode.MEDIA_RESOLUTION_REQUIRED)


def serialization_error(detail: str) -> RelayError:
    """The payload cannot be serialized or deserialized.

    Args:
        detail: Human-readable description of the serialization failure.

    Returns:
        A ``RelayError`` with code ``serialization_error``.
    """
    return RelayError(detail, code=RelayErrorCode.SERIALIZATION_ERROR)


def stream_state_invalid(detail: str) -> RelayError:
    """A stream event is out of order or from the wrong source format.

    Args:
        detail: The ordering or format violation.

    Returns:
        A ``RelayError`` with code ``stream_state_invalid``.
    """
    return RelayError(detail, code=RelayErrorCode.STREAM_STATE_INVALID)


def stream_already_finalized(detail: str) -> RelayError:
    """An event was accepted after the stream was finalized.

    Args:
        detail: What was accepted after finalization.

    Returns:
        A ``RelayError`` with code ``stream_already_finalized``.
    """
    return RelayError(detail, code=RelayErrorCode.STREAM_ALREADY_FINALIZED)


def translate(exc: Exception, *, detail: str) -> RelayError:
    """Translate an unexpected exception into a stable error category.

    ``RelayError`` passes through unchanged.  DTO parsing failures
    (``ValueError``, ``TypeError``, ``KeyError``) become
    ``malformed_payload``; any other exception becomes
    ``serialization_error``.

    Args:
        exc: The exception raised inside a mapper.
        detail: Context describing what was being translated.

    Returns:
        A stable ``RelayError``.
    """
    if isinstance(exc, RelayError):
        return exc
    if isinstance(exc, (ValueError, TypeError, KeyError)):
        return malformed_payload(detail)
    return RelayError(detail, code=RelayErrorCode.SERIALIZATION_ERROR)

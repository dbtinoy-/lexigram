"""BSON codec configuration for MongoDB."""

from __future__ import annotations

from typing import Any


def configure_codecs() -> Any:
    """Create BSON codec options for the MongoDB backend.

    Configures UUID representation and other codec settings
    for consistent serialization / deserialization.

    Returns:
        A ``CodecOptions`` instance for use with motor client.
    """
    try:
        from bson.binary import UuidRepresentation  # type: ignore[import-not-found]
        from bson.codec_options import CodecOptions  # type: ignore[import-not-found]

        return CodecOptions(uuid_representation=UuidRepresentation.STANDARD)
    except ImportError:
        return None


__all__ = ["configure_codecs"]

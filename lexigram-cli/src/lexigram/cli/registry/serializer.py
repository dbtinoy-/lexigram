"""AsyncStringSerializerProtocol registry for data serialization.

This module provides a registry pattern for data serializers (JSON, YAML, MessagePack, etc).
"""

from __future__ import annotations

import abc
import base64
from datetime import date, datetime
from decimal import Decimal
from typing import Any, ClassVar

from lexigram import serialization as json


class AsyncStringSerializerProtocol(abc.ABC):
    """Abstract base class for serializers."""

    name: ClassVar[str]
    content_type: ClassVar[str]
    file_extension: ClassVar[str]

    @abc.abstractmethod
    def serialize(self, data: Any) -> str | bytes:
        """Serialize data to string or bytes."""

    @abc.abstractmethod
    def deserialize(self, data: str | bytes) -> Any:
        """Deserialize data from string or bytes."""


class JSONSerializer(AsyncStringSerializerProtocol):
    """JSON serializer."""

    name = "json"
    content_type = "application/json"
    file_extension = "json"

    def serialize(self, data: Any) -> str:
        return json.dumps(data, indent=2, default=self._json_serial).decode("utf-8")

    def deserialize(self, data: str | bytes) -> Any:
        return json.loads(data)

    @staticmethod
    def _json_serial(obj: Any) -> Any:
        if isinstance(obj, (datetime, date)):
            return obj.isoformat()
        if isinstance(obj, Decimal):
            return float(obj)
        if isinstance(obj, bytes):
            return base64.b64encode(obj).decode()
        raise TypeError(f"Type {type(obj)} not serializable")


class CompactJSONSerializer(AsyncStringSerializerProtocol):
    """Compact JSON serializer (no indentation)."""

    name = "json-minified"
    content_type = "application/json"
    file_extension = "json"

    def serialize(self, data: Any) -> str:
        return json.dumps(
            data,
            separators=(",", ":"),
            default=JSONSerializer._json_serial,
        ).decode("utf-8")

    def deserialize(self, data: str | bytes) -> Any:
        return json.loads(data)


class YAMLSerializer(AsyncStringSerializerProtocol):
    """YAML serializer."""

    name = "yaml"
    content_type = "application/x-yaml"
    file_extension = "yaml"

    def serialize(self, data: Any) -> str:
        try:
            import yaml

            return yaml.dump(data, default_flow_style=False, sort_keys=False)
        except ImportError:
            return json.dumps(data, indent=2).decode("utf-8")

    def deserialize(self, data: str | bytes) -> Any:
        try:
            import yaml
            from yaml import SafeLoader
        except ImportError:
            raise ImportError("PyYAML not installed") from None

        return yaml.load(data, Loader=SafeLoader)


class MessagePackSerializer(AsyncStringSerializerProtocol):
    """MessagePack serializer."""

    name = "msgpack"
    content_type = "application/msgpack"
    file_extension = "msgpack"

    def serialize(self, data: Any) -> bytes:
        try:
            import msgpack
        except ImportError:
            raise ImportError("msgpack not installed") from None

        return msgpack.packb(data, use_bin_type=True)

    def deserialize(self, data: str | bytes) -> Any:
        try:
            import msgpack
        except ImportError:
            raise ImportError("msgpack not installed") from None

        if isinstance(data, str):
            data = data.encode("utf-8")
        return msgpack.unpackb(data, raw=False)


class CBORSerializer(AsyncStringSerializerProtocol):
    """CBOR serializer."""

    name = "cbor"
    content_type = "application/cbor"
    file_extension = "cbor"

    def serialize(self, data: Any) -> bytes:
        try:
            import cbor2  # type: ignore[import-not-found]
        except ImportError:
            raise ImportError("cbor2 not installed") from None

        return cbor2.dumps(data)

    def deserialize(self, data: str | bytes) -> Any:
        try:
            import cbor2
        except ImportError:
            raise ImportError("cbor2 not installed") from None

        if isinstance(data, str):
            data = data.encode("utf-8")
        return cbor2.loads(data)


class TOMLSerializer(AsyncStringSerializerProtocol):
    """TOML serializer."""

    name = "toml"
    content_type = "application/toml"
    file_extension = "toml"

    def serialize(self, data: Any) -> str:
        try:
            import tomli  # noqa: F401
            import tomli_w  # type: ignore[import-not-found]
        except ImportError:
            raise ImportError("tomli not installed") from None

        import io

        output = io.BytesIO()
        tomli_w.dump(data, output)
        return output.getvalue().decode("utf-8")

    def deserialize(self, data: str | bytes) -> Any:
        try:
            import tomllib
        except ImportError:
            try:
                import tomli as tomllib  # type: ignore[no-redef]
            except ImportError:
                raise ImportError("tomli not installed") from None

        if isinstance(data, bytes):
            data = data.decode("utf-8")
        return tomllib.loads(data)


class PickleSerializer(AsyncStringSerializerProtocol):
    """Python pickle serializer."""

    name = "pickle"
    content_type = "application/python-pickle"
    file_extension = "pkl"

    def serialize(self, data: Any) -> bytes:
        import pickle

        return pickle.dumps(data)

    def deserialize(self, data: str | bytes) -> Any:
        import pickle

        if isinstance(data, str):
            data = data.encode("utf-8")
        return pickle.loads(data)


class SerializerRegistry:
    """Registry for serializers.

    Provides a pluggable way to add new serializers.
    """

    def __init__(self) -> None:
        self._serializers: dict[str, AsyncStringSerializerProtocol] = {}
        self._initialized: bool = False

    def register(self, serializer: type[AsyncStringSerializerProtocol]) -> None:
        """Register a serializer class."""
        instance = serializer()
        self._serializers[serializer.name] = instance

    def get(self, name: str) -> AsyncStringSerializerProtocol | None:
        """Get a serializer by name."""
        self.register_defaults()
        return self._serializers.get(name)

    def get_all(self) -> dict[str, AsyncStringSerializerProtocol]:
        """Get all registered serializers."""
        self.register_defaults()
        return self._serializers.copy()

    def get_choices(self) -> list[str]:
        """Get list of available serializer names."""
        self.register_defaults()
        return list(self._serializers.keys())

    def register_defaults(self) -> None:
        """Initialize default serializers if not already done."""
        if not self._initialized:
            self.register(JSONSerializer)
            self.register(CompactJSONSerializer)
            self.register(YAMLSerializer)
            self.register(MessagePackSerializer)
            self.register(CBORSerializer)
            self.register(TOMLSerializer)
            self.register(PickleSerializer)
            self._initialized = True


def serialize(data: Any, file_format: str = "json") -> str | bytes:
    """Serialize data using the specified format."""
    serializer = SerializerRegistry().get(file_format)
    if not serializer:
        raise ValueError(f"Unknown format: {file_format}")
    return serializer.serialize(data)


def deserialize(data: str | bytes, file_format: str = "json") -> Any:
    """Deserialize data using the specified format."""
    serializer = SerializerRegistry().get(file_format)
    if not serializer:
        raise ValueError(f"Unknown format: {file_format}")
    return serializer.deserialize(data)


__all__ = [
    "AsyncStringSerializerProtocol",
    "CBORSerializer",
    "CompactJSONSerializer",
    "JSONSerializer",
    "MessagePackSerializer",
    "PickleSerializer",
    "SerializerRegistry",
    "TOMLSerializer",
    "YAMLSerializer",
    "deserialize",
    "serialize",
]

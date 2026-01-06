from __future__ import annotations

import inspect
from typing import Any, get_origin
from typing import Union as UnionType

from lexigram.contracts.exceptions import ProtocolValidationError


def validate_protocol(instance: Any, protocol: type[Any]) -> None:
    """Validate that an instance satisfies a protocol interface at runtime.

    Checks that the instance has all public members declared by the protocol.
    Callable members must also be callable on the implementation.

    Args:
        instance: The object to validate.
        protocol: The protocol type to validate against.

    Raises:
        TypeError: If the instance does not satisfy the protocol.
    """
    _validate_members(instance, protocol)


def validate_protocol_static(impl_class: type[Any], protocol: type[Any]) -> None:
    """Validate that a class satisfies a protocol interface (static check).

    Like :func:`validate_protocol` but accepts a class rather than
    an instance.

    Args:
        impl_class: The class to validate.
        protocol: The protocol type to validate against.

    Raises:
        TypeError: If the class does not satisfy the protocol.
    """
    _validate_members(impl_class, protocol)


def _validate_members(target: Any, protocol: type[Any]) -> None:
    """Check that *target* exposes every public member of *protocol*."""
    protocol_members = _get_protocol_members(protocol)
    target_cls = target if inspect.isclass(target) else type(target)

    for name, expected_member in protocol_members.items():
        if not hasattr(target, name):
            raise TypeError(
                f"'{target_cls.__name__}' is missing member '{name}' "
                f"required by protocol '{protocol.__name__}'",
            )

        if callable(expected_member):
            actual_member = getattr(target, name)
            if not callable(actual_member):
                raise TypeError(
                    f"'{name}' in '{target_cls.__name__}' must be callable "
                    f"as defined in protocol '{protocol.__name__}'",
                )


def _get_protocol_members(protocol: type[Any]) -> dict[str, Any]:
    """Extract public members defined in *protocol* and its bases."""
    members: dict[str, Any] = {}

    for base in inspect.getmro(protocol):
        if base.__module__ in ("typing", "builtins", "abc"):
            continue

        for name, value in base.__dict__.items():
            if name.startswith("_"):
                continue

            members[name] = value

        if hasattr(base, "__annotations__"):
            for name in base.__annotations__:
                if not name.startswith("_"):
                    members[name] = None  # Marker for annotated attributes

    return members


class ProtocolValidator:
    """Validates service registrations and resolutions against protocols.

    Ensures that registered services conform to their declared protocols
    and that resolved services match expected protocol requirements.
    """

    def validate_registration(self, service_type: type, implementation: Any) -> None:
        """Validate that an implementation conforms to a protocol.

        Args:
            service_type: The protocol or type being registered.
            implementation: The implementation instance or class.

        Raises:
            ProtocolValidationError: If validation fails.
        """
        if not self._is_protocol(service_type):
            return  # Not a protocol, skip validation

        # If implementation is a function/lambda/method (and not a class), it's a factory.
        if (
            inspect.isfunction(implementation) or inspect.ismethod(implementation)
        ) and not inspect.isclass(implementation):
            # Validate the factory's return-type annotation against the protocol
            hints = inspect.get_annotations(implementation, eval_str=False)
            return_hint = hints.get("return")
            if return_hint is not None and inspect.isclass(return_hint):
                try:
                    validate_protocol_static(return_hint, service_type)
                except (TypeError, ValueError, AttributeError) as exc:
                    raise ProtocolValidationError(
                        f"Factory return type does not conform to protocol "
                        f"{getattr(service_type, '__name__', service_type)}: {exc}",
                    ) from exc
            return

        try:
            if inspect.isclass(implementation):
                validate_protocol_static(implementation, service_type)
            else:
                validate_protocol(implementation, service_type)
        except (TypeError, ValueError, AttributeError) as exc:
            raise ProtocolValidationError(
                f"Validation failed for protocol {getattr(service_type, '__name__', service_type)}: {exc}",
            ) from exc

    def validate_resolution(self, resolved_service: Any, expected_type: type) -> None:
        """Validate that a resolved service matches the expected type/protocol.

        Args:
            resolved_service: The resolved service instance.
            expected_type: The expected type or protocol.

        Raises:
            ProtocolValidationError: If validation fails.
        """
        if not self._is_protocol(expected_type):
            # Regular type checking
            if not isinstance(resolved_service, expected_type):
                raise ProtocolValidationError(
                    f"Resolved service {resolved_service} is not an instance of {expected_type}",
                )
            return

        # Protocol validation
        try:
            validate_protocol(resolved_service, expected_type)
        except (TypeError, ValueError, AttributeError) as exc:
            raise ProtocolValidationError(
                f"Resolved service does not conform to protocol {expected_type}: {exc}",
            ) from exc

    def _is_protocol(self, obj: Any) -> bool:
        """Check if an object is a Protocol."""
        if not isinstance(obj, type):
            return False

        return getattr(obj, "_is_protocol", False) or (
            hasattr(obj, "__mro__")
            and any(getattr(base, "_is_protocol", False) for base in obj.__mro__)
        )

    def _normalize_type(self, t: Any) -> Any:
        """Normalize a type for comparison."""
        # Handle Union types
        if get_origin(t) is UnionType:
            # For Union, we can't easily validate, so skip
            return None

        # Handle generic types
        origin = get_origin(t)
        if origin is not None:
            return origin

        return t

"""Configuration for the domain subsystem.

Domain primitives (entities, value objects, aggregates) have no
infrastructure dependencies.  :class:`DomainConfig` provides extension
points for future domain-level configuration without breaking the
package root-file contract.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class DomainConfig:
    """Domain subsystem configuration.

    Currently a minimal configuration with no required fields.
    Reserved for future domain-level options (e.g. strict entity
    immutability enforcement, custom ID generator registration).

    Attributes:
        strict_immutability: When True, value objects raise on mutation
            attempts at runtime.  Defaults to False for compatibility.
        id_prefix: Optional string prefix appended to auto-generated
            entity IDs for namespacing.  Empty string disables prefixing.
    """

    strict_immutability: bool = False
    id_prefix: str = ""


__all__ = ["DomainConfig"]

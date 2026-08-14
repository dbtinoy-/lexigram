"""Runtime namespace helper for contributor-supplied Resource classes."""

from __future__ import annotations

import re

_CACHE: dict[tuple[type, str], type] = {}


def _sanitize_package_segment(namespaced_name: str) -> str:
    """Return *namespaced_name* with non-slug characters replaced by underscores.

    Contributor package sources are distribution names, where hyphens are
    legal ("lexigram-template"); resource slugs only allow ``[a-z0-9_]``.
    The package portion is sanitized so the namespaced name passes
    :func:`lexigram.admin.resources.base._validate_resource_name`.

    Args:
        namespaced_name: Dotted provider-package name.

    Returns:
        The sanitized dotted name.
    """
    package, _, slug = namespaced_name.partition(".")
    safe_package = re.sub(r"[^a-z0-9_]", "_", package.lower())
    return f"{safe_package}.{slug}" if slug else safe_package


def apply_namespace(resource_cls: type, namespaced_name: str) -> type:
    """Return a subclass of *resource_cls* with its name set to *namespaced_name*.

    The returned class inherits all attributes from the original and adds a
    ``route_prefix`` derived from the dotted name:
    ``"fake_pkg.users"`` → ``route_prefix = "/fake_pkg/users"``.

    Idempotent: calling twice with the same arguments returns the same class.
    """
    safe_name = _sanitize_package_segment(namespaced_name)
    key = (resource_cls, safe_name)
    if key in _CACHE:
        return _CACHE[key]

    package, _, slug = safe_name.partition(".")
    route_prefix = f"/{package}/{slug}"

    wrapped = type(
        f"Namespaced_{resource_cls.__name__}",
        (resource_cls,),
        {
            "name": safe_name,
            "route_prefix": route_prefix,
        },
    )
    _CACHE[key] = wrapped
    return wrapped

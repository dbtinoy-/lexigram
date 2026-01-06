"""Runtime namespace helper for contributor-supplied Resource classes."""

from __future__ import annotations

_CACHE: dict[tuple[type, str], type] = {}


def apply_namespace(resource_cls: type, namespaced_name: str) -> type:
    """Return a subclass of *resource_cls* with its name set to *namespaced_name*.

    The returned class inherits all attributes from the original and adds a
    ``route_prefix`` derived from the dotted name:
    ``"fake_pkg.users"`` → ``route_prefix = "/fake_pkg/users"``.

    Idempotent: calling twice with the same arguments returns the same class.
    """
    key = (resource_cls, namespaced_name)
    if key in _CACHE:
        return _CACHE[key]

    package, _, slug = namespaced_name.partition(".")
    route_prefix = f"/{package}/{slug}"

    wrapped = type(
        f"Namespaced_{resource_cls.__name__}",
        (resource_cls,),
        {
            "name": namespaced_name,
            "route_prefix": route_prefix,
        },
    )
    _CACHE[key] = wrapped
    return wrapped

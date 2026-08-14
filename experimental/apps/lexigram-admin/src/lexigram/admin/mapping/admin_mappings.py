"""Admin mapping registrations.

Wires up all AdminObjectMapper mappings between admin domain objects.
Call :func:`register_admin_mappings` once during provider boot to make all
mappings available.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.admin.auth.entity import AdminUserEntity
from lexigram.admin.auth.user import AdminUserRecord

if TYPE_CHECKING:
    from lexigram.admin.mapping.mapper import AdminObjectMapper


def _entity_to_record(entity: AdminUserEntity) -> AdminUserRecord:
    """Map :class:`AdminUserEntity` → :class:`AdminUserRecord`."""
    return entity.to_user()


def _entity_to_dict(entity: AdminUserEntity) -> dict[str, Any]:
    """Map :class:`AdminUserEntity` → plain dict."""
    return {
        "id": entity.id,
        "username": entity.username,
        "email": entity.email,
        "roles": list(entity.roles),
        "permissions": list(entity.permissions),
        "is_active": entity.is_active,
        "is_verified": entity.is_verified,
        "created_at": entity.created_at.isoformat(),
        "updated_at": entity.updated_at.isoformat() if entity.updated_at else None,
    }


def _record_to_entity(record: AdminUserRecord) -> AdminUserEntity:
    """Map :class:`AdminUserRecord` → :class:`AdminUserEntity`."""
    return AdminUserEntity.from_user(record)


def register_admin_mappings(mapper: AdminObjectMapper) -> None:
    """Register all admin domain object mappings on *mapper*.

    Args:
        mapper: The :class:`~lexigram.admin.mapping.mapper.AdminObjectMapper`
            instance to register mappings on.
    """
    mapper.register(AdminUserEntity, AdminUserRecord, _entity_to_record)
    mapper.register(AdminUserEntity, dict, _entity_to_dict)
    mapper.register(AdminUserRecord, AdminUserEntity, _record_to_entity)


__all__ = ["register_admin_mappings"]

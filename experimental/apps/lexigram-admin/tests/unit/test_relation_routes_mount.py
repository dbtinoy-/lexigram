"""Relation-route mounting through the production router.

``resource.relations`` must register ``register_relation_routes`` output on
the resource's route set — the wiring that used to live behind the retired
``ViewPage`` path.
"""

from __future__ import annotations

from lexigram.admin.config import AdminConfig
from lexigram.admin.core.routing import AdminRouter
from lexigram.admin.relations import RelationManager


class _PetsRelationManager(RelationManager):
    relationship_name = "pets"


class _Resource:
    name = "users"
    _data_source = object()
    relations = [_PetsRelationManager]


def test_relation_routes_are_mounted_for_resource() -> None:
    router = AdminRouter(config=AdminConfig(prefix="/admin"))
    routes = router._build_resource_routes("users", _Resource())
    paths = [route.path for route in routes]
    assert "/users/{parent_id}/relations/{rel_name}" in paths
    assert "/users/{parent_id}/relations/{rel_name}/new" in paths
    assert "/users/{parent_id}/relations/{rel_name}/{record_id}/edit" in paths

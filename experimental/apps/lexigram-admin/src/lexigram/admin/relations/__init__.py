"""Relations module for lexigram-admin.

Provides relation managers for managing entity relationships
in admin views, including many-to-many with pivot data,
polymorphic relations, and inline CRUD.
"""

from __future__ import annotations

from lexigram.admin.relations.belongs_to_many import BelongsToManyRelationManager
from lexigram.admin.relations.manager import AbstractRelationManager
from lexigram.admin.relations.manager_ext import RelationManager
from lexigram.admin.relations.morph_many import MorphManyRelationManager
from lexigram.admin.relations.morph_to import MorphToRelationManager
from lexigram.admin.relations.routes import register_relation_routes

__all__ = [
    "AbstractRelationManager",
    "BelongsToManyRelationManager",
    "MorphManyRelationManager",
    "MorphToRelationManager",
    "RelationManager",
    "register_relation_routes",
]

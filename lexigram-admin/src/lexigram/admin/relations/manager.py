"""Relation manager for lexigram-admin.

Provides base class for managing entity relationships in admin views.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from lexigram.ui.columns.types import Column
from lexigram.di.decorators import inject


@inject
class AbstractRelationManager(ABC):
    """Base class for managing entity relationships.

    Subclasses define how to display and query related entities
    for a parent resource.

    Example:
        class UserPetsRelationManager(AbstractRelationManager):
            relationship_name = "pets"

            @classmethod
            def table(cls, table_config=None):
                return [
                    TextColumn("name").sortable(),
                    BadgeColumn("species"),
                ]

            async def get_query(self):
                return await pet_service.list(user_id=self.parent_id)
    """

    relationship_name: ClassVar[str] = ""

    def __init__(
        self,
        parent_id: Any = None,
        parent: Any = None,
        data_source: Any = None,
    ):
        """Initialize relation manager.

        Args:
            parent_id: ID of the parent entity
            parent: The parent entity object (optional)
            data_source: Optional data source used for persisting
                pivot/relation operations. Subclasses may also attach
                one later via :meth:`set_data_source`.
        """
        self.parent_id = parent_id
        self.parent = parent
        self._data_source = data_source

    def set_data_source(self, data_source: Any) -> None:
        """Attach a data source for pivot persistence operations."""
        self._data_source = data_source

    @classmethod
    @abstractmethod
    def table(cls, table_config: Any = None) -> list[Column]:
        """Define columns for displaying related entities.

        Args:
            table_config: Optional table configuration

        Returns:
            List of Column instances
        """
        ...

    @abstractmethod
    async def get_query(self) -> list[Any]:
        """Get related entities for the parent.

        Returns:
            List of related entities
        """
        ...

    async def count(self) -> int:
        """Count related entities.

        Returns:
            Number of related entities
        """
        items = await self.get_query()
        return len(items) if items else 0

    async def get_items(
        self,
        *,
        page: int = 1,
        per_page: int = 20,
        **filters: Any,
    ) -> list[Any]:
        """Get paginated related entities.

        Args:
            page: Page number (1-indexed)
            per_page: Items per page
            **filters: Additional filters

        Returns:
            List of related entities for the page
        """
        items = await self.get_query()
        if not items:
            return []

        start = (page - 1) * per_page
        end = start + per_page
        return items[start:end]

    @classmethod
    def get_relationship_name(cls) -> str:
        """Get the name of this relationship."""
        return cls.relationship_name or cls.__name__.lower().replace(
            "relationmanager",
            "",
        )


__all__ = ["AbstractRelationManager"]

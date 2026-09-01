"""Resource CRUD controller (package facade).

Provides a base controller class for handling resource CRUD with
HTMX support, automatic pagination, filtering, and bulk actions.
Method implementations live in sibling mixin modules.
"""

from __future__ import annotations

from abc import ABC
from typing import Generic

from lexigram.admin.controllers.resource.bulk import ResourceBulkMixin
from lexigram.admin.controllers.resource.core import ResourceCoreMixin
from lexigram.admin.controllers.resource.detail import ResourceDetailMixin
from lexigram.admin.controllers.resource.imports import ResourceImportMixin
from lexigram.admin.controllers.resource.list import ResourceListMixin
from lexigram.admin.controllers.resource.meta import ResourceMeta, T
from lexigram.admin.controllers.resource.mutation import ResourceMutationMixin
from lexigram.admin.controllers.resource.render import ResourceRenderMixin
from lexigram.admin.controllers.resource.revisions import ResourceRevisionMixin
from lexigram.admin.controllers.resource.routes import ResourceRouteMixin
from lexigram.di.decorators import inject

__all__ = ["ResourceController", "ResourceMeta", "T"]


@inject
class ResourceController(
    ResourceCoreMixin,
    ResourceListMixin,
    ResourceDetailMixin,
    ResourceMutationMixin,
    ResourceBulkMixin,
    ResourceImportMixin,
    ResourceRevisionMixin,
    ResourceRenderMixin,
    ResourceRouteMixin,
    ABC,
    Generic[T],
):
    """Base controller for resource CRUD operations.

    Provides standard CRUD endpoints with HTMX support:
    - GET  /{resource}           - List with pagination/filtering
    - GET  /{resource}/{id}      - View single resource
    - GET  /{resource}/create    - Create form
    - POST /{resource}           - Create resource
    - GET  /{resource}/{id}/edit - Edit form
    - PUT  /{resource}/{id}      - Update resource
    - DELETE /{resource}/{id}    - Delete resource
    - POST /{resource}/bulk      - Bulk actions

    Subclasses should implement:
    - get_data_source() - Return DataSourceProtocol for this resource
    - get_columns() - Return columns for list view
    - render_list() - Render list view HTML
    - render_detail() - Render detail view HTML
    - render_form() - Render create/edit form HTML
    """

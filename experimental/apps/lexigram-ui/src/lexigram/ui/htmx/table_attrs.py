"""
Centralized HTMX attribute generation for Lexigram Admin.

This module provides a type-safe, consistent way to generate HTMX attributes
for different action types. All components should use these builders rather
than constructing hx-* attributes manually.

Key Patterns:
1. Full Refresh - Replace entire table (layout/view changes)
2. Data Refresh - Update data zone only (filter/sort/page changes)
3. Modal/SlideOver - Open overlay for forms
4. OOB - Out-of-band updates for multiple zones

The "Baked URL" Pattern:
Instead of using hx-include to gather inputs at request time, we "bake"
all state into the URL upfront. This is more reliable and easier to debug.

    # BEFORE (problematic)
    attrs = {"hx-get": "/users/", "hx-include": "#table [name]"}

    # AFTER (robust)
    attrs = HTMXAttrs.for_data_refresh(state, "/users/")
    # Results in: {"hx-get": "/users/?page=1&search=...", "hx-params": "none"}
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any, Literal
from urllib.parse import urlencode

from lexigram.ui import Zone, Zones

if TYPE_CHECKING:
    from lexigram.ui.state import TableState


ActionType = Literal[
    "full_refresh",  # Replace TABLE zone
    "data_refresh",  # Replace DATA zone
    "modal",  # Open in MODAL zone
    "slide_over",  # Open in SLIDE_OVER zone
    "oob",  # Out-of-band update
]


@dataclass
class HTMXAttrsBuilder:
    """
    Builder for consistent HTMX attributes.

    This class encapsulates the logic for generating correct HTMX attributes
    for different action types. Use the static methods on HTMXAttrs for
    convenience unless you need custom configuration.

    Attributes:
        action: The type of action (determines target zone and swap mode)
        state: The current TableState (used for baked URLs)
        resource_prefix: The base URL for the resource (e.g., "/admin/users")
        extra_params: Additional query parameters to include
        push_url: Whether to update browser history (default: True for refresh actions)
        confirm_message: Optional confirmation dialog message
    """

    action: ActionType
    state: TableState
    resource_prefix: str
    extra_params: dict = field(default_factory=dict)
    push_url: bool | None = None  # None = use action default
    confirm_message: str | None = None

    def build(self) -> dict[str, str]:
        """
        Generate HTMX attributes based on action type.

        Returns a dict of hx-* attributes ready to be spread onto an element.
        """
        params = self.state.to_query_params()
        if self.extra_params:
            params.update(self.extra_params)

        base_url = self.resource_prefix.rstrip("/")

        if self.action == "full_refresh":
            return self._build_full_refresh(base_url, params)
        if self.action == "data_refresh":
            return self._build_data_refresh(base_url, params)
        if self.action == "modal":
            return self._build_modal(base_url)
        if self.action == "slide_over":
            return self._build_slide_over(base_url)
        if self.action == "oob":
            return self._build_oob(base_url, params)

        raise ValueError(f"Unknown action type: {self.action}")

    def _build_full_refresh(self, base_url: str, params: dict) -> dict[str, str]:
        """Full refresh: Replace entire table zone with outerHTML."""
        query = urlencode(params, doseq=True) if params else ""
        # No trailing slash: resource routes are registered as "/{name}"
        # (core/routing.py), so "/{name}/" 307-redirects on every request.
        url = f"{base_url}?{query}" if query else base_url

        push = self.push_url if self.push_url is not None else True

        attrs = {
            "hx-get": url,
            "hx-target": Zones.TABLE.selector,
            "hx-swap": Zones.TABLE.swap_mode.value,
            "hx-params": "none",  # URL has everything
            "hx-push-url": "true" if push else "false",
        }

        if self.confirm_message:
            attrs["hx-confirm"] = self.confirm_message

        return attrs

    def _build_data_refresh(self, base_url: str, params: dict) -> dict[str, str]:
        """Data refresh: Replace data zone, extract from full response."""
        query = urlencode(params, doseq=True) if params else ""
        # No trailing slash: resource routes are registered as "/{name}"
        # (core/routing.py), so "/{name}/" 307-redirects on every request.
        url = f"{base_url}?{query}" if query else base_url

        push = self.push_url if self.push_url is not None else True

        attrs = {
            "hx-get": url,
            "hx-target": Zones.DATA.selector,
            # outerHTML, not the zone's innerHTML default: hx-select extracts
            # the #table-data wrapper itself, so an innerHTML swap nested a
            # second #table-data inside the live one. getElementById then
            # resolved to the outer node and the next swap replaced the
            # subtree the user was looking at -- the URL changed and the view
            # did not.
            "hx-swap": "outerHTML",
            "hx-select": Zones.DATA.selector,  # Extract only DATA from response
            # hx-select discards anything outside the selected subtree, which
            # would drop the toolbar/tab OOB fragments the server sends.
            "hx-select-oob": Zones.data_refresh_oob_select(),
            "hx-params": "none",
            "hx-push-url": "true" if push else "false",
        }

        if self.confirm_message:
            attrs["hx-confirm"] = self.confirm_message

        return attrs

    def _build_modal(self, base_url: str) -> dict[str, str]:
        """Modal: Load content into modal container."""
        return {
            "hx-get": base_url,
            "hx-target": Zones.MODAL.selector,
            "hx-swap": Zones.MODAL.swap_mode.value,
            "hx-push-url": "false",  # Don't update URL for modals
        }

    def _build_slide_over(self, base_url: str) -> dict[str, str]:
        """Slide-over: Load content into side panel."""
        return {
            "hx-get": base_url,
            "hx-target": Zones.SLIDE_OVER.selector,
            "hx-swap": Zones.SLIDE_OVER.swap_mode.value,
            "hx-push-url": "false",
        }

    def _build_oob(self, base_url: str, params: dict) -> dict[str, str]:
        """OOB: Request that returns out-of-band fragments."""
        query = urlencode(params, doseq=True) if params else ""
        # No trailing slash: resource routes are registered as "/{name}"
        # (core/routing.py), so "/{name}/" 307-redirects on every request.
        url = f"{base_url}?{query}" if query else base_url

        # OOB requests typically don't need a primary target
        # The server response includes hx-swap-oob fragments
        return {
            "hx-get": url,
            "hx-params": "none",
        }


class HTMXAttrs:
    """
    Factory for HTMX attributes.

    This class provides convenient static methods for generating HTMX
    attributes for common use cases. For more control, use HTMXAttrsBuilder
    directly.

    Examples:
        # Data refresh (filter, sort, paginate)
        attrs = HTMXAttrs.for_data_refresh(state, "/admin/users")

        # Full refresh (layout/view change)
        attrs = HTMXAttrs.for_full_refresh(state, "/admin/users")

        # Delete with confirmation
        attrs = HTMXAttrs.for_delete("/admin/users/123", confirm="Delete this user?")

        # Bulk action
        attrs = HTMXAttrs.for_bulk_action("/admin/users/bulk/delete", "DELETE")
    """

    @staticmethod
    def for_full_refresh(
        state: TableState,
        resource_prefix: str,
        push_url: bool = True,
        **extra_params: Any,
    ) -> dict[str, str]:
        """
        Generate HTMX attributes for a full table refresh.

        Use for: Layout changes, view changes, clearing all filters.

        Args:
            state: Current table state
            resource_prefix: Base URL (e.g., "/admin/users")
            push_url: Update browser history (default True)
            **extra_params: Additional query parameters

        Returns:
            Dict of hx-* attributes
        """
        return HTMXAttrsBuilder(
            action="full_refresh",
            state=state,
            resource_prefix=resource_prefix,
            extra_params=extra_params or {},
            push_url=push_url,
        ).build()

    @staticmethod
    def for_data_refresh(
        state: TableState,
        resource_prefix: str,
        push_url: bool = True,
        **extra_params: Any,
    ) -> dict[str, str]:
        """
        Generate HTMX attributes for a data zone refresh.

        Use for: Filtering, sorting, pagination, search.

        Args:
            state: Current table state
            resource_prefix: Base URL
            push_url: Update browser history (default True)
            **extra_params: Additional query parameters

        Returns:
            Dict of hx-* attributes
        """
        return HTMXAttrsBuilder(
            action="data_refresh",
            state=state,
            resource_prefix=resource_prefix,
            extra_params=extra_params or {},
            push_url=push_url,
        ).build()

    @staticmethod
    def for_modal(
        url: str,
    ) -> dict[str, str]:
        """
        Generate HTMX attributes for opening a modal.

        Args:
            url: URL to load into modal

        Returns:
            Dict of hx-* attributes
        """
        return {
            "hx-get": url,
            "hx-target": Zones.MODAL.selector,
            "hx-swap": Zones.MODAL.swap_mode.value,
            "hx-push-url": "false",
        }

    @staticmethod
    def for_slide_over(
        url: str,
    ) -> dict[str, str]:
        """
        Generate HTMX attributes for opening a slide-over panel.

        Args:
            url: URL to load into slide-over

        Returns:
            Dict of hx-* attributes
        """
        return {
            "hx-get": url,
            "hx-target": Zones.SLIDE_OVER.selector,
            "hx-swap": Zones.SLIDE_OVER.swap_mode.value,
            "hx-push-url": "false",
        }

    @staticmethod
    def for_delete(
        url: str,
        target_zone: Zone | None = None,
        confirm_message: str | None = None,
    ) -> dict[str, str]:
        """
        Generate HTMX attributes for a delete action.

        Args:
            url: Delete endpoint URL
            target_zone: Zone to update after delete (default: DATA)
            confirm_message: Optional confirmation dialog

        Returns:
            Dict of hx-* attributes
        """
        zone = target_zone or Zones.DATA

        attrs = {
            "hx-delete": url,
            "hx-target": zone.selector,
            "hx-swap": zone.swap_mode.value,
        }

        if confirm_message:
            attrs["hx-confirm"] = confirm_message

        return attrs

    @staticmethod
    def for_bulk_action(
        url: str,
        method: str = "POST",
        confirm_message: str | None = None,
        action_name: str | None = None,
    ) -> dict[str, str]:
        """
        Generate HTMX attributes for a bulk action.

        Bulk actions include the checked checkboxes from the table
        plus the action name so the server can dispatch correctly.

        Args:
            url: Bulk action endpoint URL
            method: HTTP method (POST, DELETE, etc.)
            confirm_message: Optional confirmation dialog
            action_name: Action identifier sent as ``action`` form value

        Returns:
            Dict of hx-* attributes
        """
        attrs = {
            f"hx-{method.lower()}": url,
            "hx-target": Zones.DATA.selector,
            "hx-swap": Zones.DATA.swap_mode.value,
            # Do not set hx-params="none" here: HTMX applies that filter to
            # the request as a whole and can discard values supplied by
            # hx-include. The selector below already limits the payload to
            # checked row IDs.
            # Only include checked checkboxes
            "hx-include": f"{Zones.TABLE.selector} [name='ids']:checked",
        }

        if action_name:
            attrs["hx-vals"] = f'{{"action":"{action_name}"}}'

        if confirm_message:
            attrs["hx-confirm"] = confirm_message

        return attrs

    @staticmethod
    def for_form_submit(
        url: str,
        method: str = "POST",
        target_zone: Zone | None = None,
        _close_on_success: bool = True,
    ) -> dict[str, str]:
        """
        Generate HTMX attributes for form submission.

        Args:
            url: Form action URL
            method: HTTP method
            target_zone: Zone to update on success (default: DATA)
            close_on_success: Whether to close modal/slide-over

        Returns:
            Dict of hx-* attributes
        """
        zone = target_zone or Zones.DATA

        return {
            f"hx-{method.lower()}": url,
            "hx-target": zone.selector,
            "hx-swap": zone.swap_mode.value,
        }

        # On success, server should return OOB fragments to close overlays
        # This is handled server-side, not in attributes

    @staticmethod
    def for_live_table_input(
        _state: TableState,
        resource_prefix: str,
        input_name: str | None = None,
    ) -> dict[str, str]:
        """
        Generate HTMX attributes for a live table input (search-as-you-type).

        Exception to the baked-URL pattern: live inputs use hx-include to send
        the current input value with each keystroke, rather than baking state
        into the URL. The input value changes too frequently for URL-based state.

        Args:
            state: Current table state (not baked into URL — used for hx-include scope)
            resource_prefix: Base URL (e.g., "/admin/users")
            input_name: Optional custom name attribute for the live input selector.
                Defaults to the SEARCH zone ID.

        Returns:
            Dict of hx-* attributes for a live table input.
        """
        base_url = resource_prefix.rstrip("/")

        if input_name:
            search_selector = f'[name="{input_name}"]'
        else:
            search_selector = f"#{Zones.SEARCH.id}"

        return {
            "hx-get": base_url,
            "hx-target": Zones.DATA.selector,
            # outerHTML: hx-select extracts #table-data itself.
            "hx-swap": "outerHTML",
            "hx-select": Zones.DATA.selector,
            "hx-select-oob": Zones.data_refresh_oob_select(),
            "hx-include": (
                f"{Zones.DATA.selector} [data-state='true'], {search_selector}"
            ),
            "hx-push-url": "true",
            "hx-params": "*",
        }

    @staticmethod
    def merge(*attr_dicts: dict[str, str]) -> dict[str, str]:
        """
        Merge multiple HTMX attribute dictionaries.

        Later values override earlier ones.

        Args:
            *attr_dicts: Attribute dictionaries to merge

        Returns:
            Merged dictionary
        """
        result = {}
        for d in attr_dicts:
            result.update(d)
        return result

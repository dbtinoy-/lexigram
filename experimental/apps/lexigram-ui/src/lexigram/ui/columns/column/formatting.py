"""
Column formatting and masking methods.
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any, Self


class ColumnFormattingMixin:
    """Mixin class containing formatting and masking methods."""

    def format_state_using(self, callback: Callable[[Any], Any]) -> Self:
        """
        Custom formatting function.

        Allows you to transform the value before rendering.

        Args:
            callback: Function that takes the value and returns formatted value

        Returns:
            Self for method chaining

        Example:
            >>> def uppercase(value):
            ...     return str(value).upper()
            >>> TextColumn("name").format_state_using(uppercase)
            >>>
            >>> # Lambda example
            >>> TextColumn("price").format_state_using(lambda x: f"${x:.2f}")
        """
        self._format_callback = callback
        return self

    def mask(self, masker: Callable[[Any], str]) -> Self:
        """
        Add a data masker to the column.

        Maskers transform the value for display to protect sensitive information.

        Args:
            masker: Function that takes the value and returns a masked version

        Returns:
            Self for method chaining

        Example:
            >>> from lexigram.admin.security.masking import DataMasker
            >>> TextColumn("email").mask(DataMasker.mask_email)
        """
        self._masker = masker
        return self

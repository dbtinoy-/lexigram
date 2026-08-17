"""
Concrete column implementations for common data types.
"""

from __future__ import annotations

from datetime import UTC, date, datetime
from typing import Any

from lexigram.ui import el
from lexigram.ui.columns import Column


class TextColumn(Column):
    """Simple text column with optional formatting."""

    def __init__(self, name: str, label: str | None = None):
        super().__init__(name, label)
        self._color: str | None = None
        self._size: str = "sm"
        self._weight: str = "normal"
        self._mono = False

    def color(self, color: str) -> TextColumn:
        """Set text color (gray, red, blue, green, yellow, etc.)."""
        self._color = color
        return self

    def size(self, size: str) -> TextColumn:
        """Set text size (xs, sm, base, lg, xl)."""
        self._size = size
        return self

    def weight(self, weight: str) -> TextColumn:
        """Set font weight (normal, medium, semibold, bold)."""
        self._weight = weight
        return self

    def mono(self, mono: bool = True) -> TextColumn:
        """Use monospace font."""
        self._mono = mono
        return self

    def render(self, value: Any, record: dict) -> Any:
        """Render as styled text."""
        if value is None:
            return el("span", "—", class_="text-muted-foreground italic")

        classes = [f"text-{self._size}"]

        if self._color:
            classes.append(f"text-{self._color}-600 dark:text-{self._color}-400")
        else:
            classes.append("text-foreground")

        if self._weight != "normal":
            classes.append(f"font-{self._weight}")

        if self._mono:
            classes.append("font-mono")

        return el("span", str(value), class_="".join(classes))


class BadgeColumn(Column):
    """Status badge column with color coding."""

    def __init__(
        self,
        name: str,
        label: str | None = None,
        colors: dict[str, str] | None = None,
    ):
        """
        Initialize badge column.

        Args:
            name: Column field name
            label: Display label
            colors: Mapping of values to colors (e.g., {"active": "green", "inactive": "gray"})
        """
        super().__init__(name, label)
        self._colors = colors or {}
        self._icons: dict[str, str] = {}

    def colors(self, colors: dict[str, str]) -> BadgeColumn:
        """Set color mapping for values."""
        self._colors = colors
        return self

    def icons(self, icons: dict[str, str]) -> BadgeColumn:
        """Set icon mapping for values (emoji or icon class)."""
        self._icons = icons
        return self

    def render(self, value: Any, record: dict) -> Any:
        """Render as colored badge using atomic Badge component."""
        if value is None:
            return el("span", "—", class_="text-muted-foreground italic")

        # Import Badge component
        from lexigram.ui import Badge

        # Handle list/tuple/set values
        if isinstance(value, (list, tuple, set)):
            badges = []
            for item in value:
                item_str = str(item)
                item_lower = item_str.lower()
                color = self._colors.get(item_lower, "gray")
                icon = self._icons.get(item_lower, "")
                badge_text = f"{icon} {item_str}" if icon else item_str
                badges.append(Badge(badge_text, variant=color).render())  # type: ignore[arg-type]

            return el("div", *badges, class_="flex flex-wrap gap-1")

        value_str = str(value).lower()
        color = self._colors.get(value_str, "gray")
        icon = self._icons.get(value_str, "")

        # Create badge with icon if present
        badge_text = f"{icon} {value}" if icon else str(value)

        # Use Badge atomic component
        badge = Badge(badge_text, variant=color)  # type: ignore[arg-type]
        return badge.render()


class BooleanColumn(Column):
    """Boolean column with icons."""

    def __init__(self, name: str, label: str | None = None):
        super().__init__(name, label)
        self._true_icon = "✓"
        self._false_icon = "✗"
        self._true_color = "green"
        self._false_color = "red"

    def true_icon(self, icon: str) -> BooleanColumn:
        """Set icon for true values."""
        self._true_icon = icon
        return self

    def false_icon(self, icon: str) -> BooleanColumn:
        """Set icon for false values."""
        self._false_icon = icon
        return self

    def true_color(self, color: str) -> BooleanColumn:
        """Set color for true values."""
        self._true_color = color
        return self

    def false_color(self, color: str) -> BooleanColumn:
        """Set color for false values."""
        self._false_color = color
        return self

    def render(self, value: Any, record: dict) -> Any:
        """Render as icon with color."""
        if value is None:
            return el("span", "—", class_="text-muted-foreground italic")

        is_true = bool(value)
        icon = self._true_icon if is_true else self._false_icon
        color = self._true_color if is_true else self._false_color

        return el(
            "span",
            icon,
            class_=f"inline-flex items-center justify-center w-6 h-6 rounded-full bg-{color}-100 dark:bg-{color}-900 text-{color}-600 dark:text-{color}-400 font-semibold",
        )


class DateColumn(Column):
    """Date/datetime column with formatting."""

    def __init__(
        self,
        name: str,
        label: str | None = None,
        date_format: str = "%Y-%m-%d",
    ):
        """
        Initialize date column.

        Args:
            name: Column field name
            label: Display label
            date_format: strftime format string
        """
        super().__init__(name, label)
        self._format = date_format
        self._relative = False
        self._timezone = None

    def format(self, date_format: str) -> DateColumn:
        """Set date format string."""
        self._format = date_format
        return self

    def date(self) -> DateColumn:
        """Format as date only (YYYY-MM-DD)."""
        self._format = "%Y-%m-%d"
        return self

    def datetime(self) -> DateColumn:
        """Format as datetime (YYYY-MM-DD HH:MM:SS)."""
        self._format = "%Y-%m-%d %H:%M:%S"
        return self

    def time(self) -> DateColumn:
        """Format as time only (HH:MM:SS)."""
        self._format = "%H:%M:%S"
        return self

    def relative(self, relative: bool = True) -> DateColumn:
        """Show relative time (e.g., '2 hours ago')."""
        self._relative = relative
        return self

    def render(self, value: Any, record: dict) -> Any:
        """Render formatted date."""
        if value is None:
            return el("span", "—", class_="text-muted-foreground italic")

        # Convert to datetime if needed
        if isinstance(value, str):
            try:
                # Try parsing ISO format
                value = datetime.fromisoformat(value.replace("Z", "+00:00"))
            except (ValueError, AttributeError):
                return el("span", str(value), class_="text-foreground")

        if isinstance(value, date) and not isinstance(value, datetime):
            value = datetime.combine(value, datetime.min.time())

        if not isinstance(value, datetime):
            return el("span", str(value), class_="text-foreground")

        # Format the date
        formatted = value.strftime(self._format)

        # Add relative time if enabled
        if self._relative:
            from datetime import timedelta

            now = datetime.now(UTC) if value.tzinfo else datetime.now()
            diff = now - value

            if diff < timedelta(minutes=1):
                relative = "just now"
            elif diff < timedelta(hours=1):
                minutes = int(diff.total_seconds() / 60)
                relative = f"{minutes}m ago"
            elif diff < timedelta(days=1):
                hours = int(diff.total_seconds() / 3600)
                relative = f"{hours}h ago"
            elif diff < timedelta(days=30):
                days = diff.days
                relative = f"{days}d ago"
            else:
                relative = formatted

            return el(
                "span",
                relative,
                class_="text-foreground",
                title=formatted,
            )

        return el("span", formatted, class_="text-foreground")


class ImageColumn(Column):
    """Image column with thumbnail preview."""

    def __init__(self, name: str, label: str | None = None):
        super().__init__(name, label)
        self._size = 10  # Default 40px (10 * 4px)
        self._rounded = True
        self._square = False

    def size(self, size: int) -> ImageColumn:
        """Set image size in Tailwind units (e.g., 10 = 40px)."""
        self._size = size
        return self

    def circular(self) -> ImageColumn:
        """Make image circular."""
        self._rounded = True
        self._square = False
        return self

    def square(self) -> ImageColumn:
        """Make image square with rounded corners."""
        self._rounded = False
        self._square = True
        return self

    def render(self, value: Any, record: dict) -> Any:
        """Render as image thumbnail."""
        if not value:
            # Placeholder
            classes = [
                "bg-muted",
                "dark:bg-muted",
                f"w-{self._size}",
                f"h-{self._size}",
            ]
            if self._rounded:
                classes.append("rounded-full")
            elif self._square:
                classes.append("rounded-md")

            return el("div", class_="".join(classes))

        classes = [f"w-{self._size}", f"h-{self._size}", "object-cover"]
        if self._rounded:
            classes.append("rounded-full")
        elif self._square:
            classes.append("rounded-md")

        return el("img", src=value, alt="", class_="".join(classes))


class CurrencyColumn(Column):
    """Currency column with formatting."""

    def __init__(self, name: str, label: str | None = None, currency: str = "USD"):
        super().__init__(name, label)
        self._currency = currency
        self._symbol = "$"
        self._decimals = 2

    def currency(self, currency: str) -> CurrencyColumn:
        """Set currency code (USD, EUR, GBP, etc.)."""
        self._currency = currency
        # Set symbol based on currency
        symbols = {
            "USD": "$",
            "EUR": "€",
            "GBP": "£",
            "JPY": "¥",
            "CNY": "¥",
        }
        self._symbol = symbols.get(currency, currency)
        return self

    def decimals(self, decimals: int) -> CurrencyColumn:
        """Set number of decimal places."""
        self._decimals = decimals
        return self

    def render(self, value: Any, record: dict) -> Any:
        """Render as formatted currency."""
        if value is None:
            return el("span", "—", class_="text-muted-foreground italic")

        try:
            amount = float(value)
            formatted = f"{amount:,.{self._decimals}f}"

            # Color based on positive/negative
            color_class = "text-foreground"
            if amount < 0:
                color_class = "text-destructive"
            elif amount > 0:
                color_class = "text-success"

            return el(
                "span",
                f"{self._symbol}{formatted}",
                class_=f"font-medium {color_class}",
            )
        except (ValueError, TypeError):
            return el("span", str(value), class_="text-foreground")


class ListColumn(Column):
    """Column for rendering lists of strings (e.g., tags, categories)."""

    def __init__(self, name: str, label: str | None = None):
        super().__init__(name, label)
        self._badge = True  # Default to badges

    def badge(self, badge: bool = True) -> ListColumn:
        """Render items as badges."""
        self._badge = badge
        return self

    def render(self, value: Any, record: dict) -> Any:
        """Render list items."""
        if not value:
            return el("span", "—", class_="text-muted-foreground italic")

        # Handle string (comma separated) or proper list
        if isinstance(value, str):
            items = list(
                filter(
                    lambda item: item.strip(),
                    (item.strip() for item in value.split(",")),
                ),
            )
        elif isinstance(value, (list, tuple, set)):
            items = list(filter(lambda item: item, (str(item) for item in value)))
        else:
            return el("span", str(value), class_="text-foreground")

        if not items:
            return el("span", "—", class_="text-muted-foreground italic")

        from lexigram.ui import Badge

        elements = []
        for item in items:
            if self._badge:
                elements.append(Badge(item, variant="gray").render())
            else:
                elements.append(
                    el("span", item, class_="text-foreground"),
                )

        container_class = (
            "flex flex-wrap gap-1" if self._badge else "flex flex-col gap-0.5"
        )
        return el("div", *elements, class_=container_class)

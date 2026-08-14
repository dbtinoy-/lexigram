from __future__ import annotations

CHART_COLORS: dict[str, str] = {
    "blue": "#3B82F6",
    "green": "#22C55E",
    "red": "#EF4444",
    "yellow": "#EAB308",
    "purple": "#A855F7",
    "primary": "var(--primary)",
    "orange": "#F97316",
    "pink": "#EC4899",
    "teal": "#14B8A6",
    "gray": "#6B7280",
    "chart-1": "var(--chart-1)",
    "chart-2": "var(--chart-2)",
    "chart-3": "var(--chart-3)",
    "chart-4": "var(--chart-4)",
    "chart-5": "var(--chart-5)",
}

CHART_BG: dict[str, str] = {
    "blue": "bg-info",
    "green": "bg-success",
    "red": "bg-destructive",
    "yellow": "bg-warning",
    "purple": "bg-purple-500",
    "primary": "bg-primary",
    "orange": "bg-orange-500",
    "pink": "bg-pink-500",
    "teal": "bg-teal-500",
    "gray": "bg-muted",
    "chart-1": "bg-chart-1",
    "chart-2": "bg-chart-2",
    "chart-3": "bg-chart-3",
    "chart-4": "bg-chart-4",
    "chart-5": "bg-chart-5",
}

CHART_TEXT: dict[str, str] = {
    "blue": "text-info",
    "green": "text-success",
    "red": "text-destructive",
    "yellow": "text-warning",
    "purple": "text-purple-600 dark:text-purple-400",
    "primary": "text-primary",
    "orange": "text-orange-600 dark:text-orange-400",
    "pink": "text-pink-600 dark:text-pink-400",
    "teal": "text-teal-600 dark:text-teal-400",
    "gray": "text-muted-foreground",
    "chart-1": "text-muted-foreground",
    "chart-2": "text-muted-foreground",
    "chart-3": "text-muted-foreground",
    "chart-4": "text-muted-foreground",
    "chart-5": "text-muted-foreground",
}


def hex_color(color_name: str) -> str:
    return CHART_COLORS.get(color_name, CHART_COLORS["blue"])


def bg_class(color_name: str) -> str:
    return CHART_BG.get(color_name, CHART_BG["blue"])


def text_class(color_name: str) -> str:
    return CHART_TEXT.get(color_name, CHART_TEXT["blue"])

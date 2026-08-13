"""Query Filters and Validation"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum
import re
from re import Pattern
from typing import Any, cast

from lexigram.search.exceptions import SearchValidationError

# Alias used by tests and external code that catches validation failures
# generically from this module.
ValidationError = SearchValidationError


class FilterType(str, Enum):
    """Filter types"""

    TEXT = "text"
    NUMBER = "number"
    DATE = "date"
    BOOLEAN = "boolean"
    ARRAY = "array"
    RANGE = "range"
    EXISTS = "exists"


@dataclass
class FilterRule:
    """Filter validation rule"""

    field: str
    type: FilterType
    required: bool = False
    min_length: int | None = None
    max_length: int | None = None
    pattern: Pattern[str] | None = None
    allowed_values: set[Any] | None = None
    min_value: int | float | None = None
    max_value: int | float | None = None
    array_item_type: FilterType | None = None


class FilterValidator:
    """Validates search filters"""

    def __init__(self, rules: list[FilterRule] | None = None):
        self.rules = rules or []
        self._field_rules = {rule.field: rule for rule in self.rules}

    def add_rule(self, rule: FilterRule) -> None:
        """Add a validation rule"""
        self.rules.append(rule)
        self._field_rules[rule.field] = rule

    def validate_filters(self, filters: dict[str, Any]) -> dict[str, Any]:
        """Validate filter dictionary"""
        validated = {}

        for field, value in filters.items():
            rule = self._field_rules.get(field)
            if rule:
                validated[field] = self._validate_field(field, value, rule)
            else:
                # No rule defined, pass through
                validated[field] = value

        # Check required fields
        for rule in self.rules:
            if rule.required and rule.field not in validated:
                raise SearchValidationError(
                    f"Required filter field '{rule.field}' is missing",
                )

        return validated

    def _validate_field(self, field: str, value: Any, rule: FilterRule) -> Any:
        """Validate a single field"""
        try:
            if rule.type == FilterType.TEXT:
                return self._validate_text(value, rule)
            if rule.type == FilterType.NUMBER:
                return self._validate_number(value, rule)
            if rule.type == FilterType.DATE:
                return self._validate_date(value, rule)
            if rule.type == FilterType.BOOLEAN:
                return self._validate_boolean(value, rule)
            if rule.type == FilterType.ARRAY:
                return self._validate_array(value, rule)
            if rule.type == FilterType.RANGE:
                return self._validate_range(value, rule)
            if rule.type == FilterType.EXISTS:
                return self._validate_exists(value, rule)
        except Exception as e:
            raise SearchValidationError(
                f"Validation failed for field '{field}': {e}"
            ) from e

    def _validate_text(self, value: Any, rule: FilterRule) -> str:
        """Validate text field"""
        if not isinstance(value, str):
            raise SearchValidationError("Value must be a string")

        if rule.min_length and len(value) < rule.min_length:
            raise SearchValidationError(
                f"String length must be at least {rule.min_length}"
            )

        if rule.max_length and len(value) > rule.max_length:
            raise SearchValidationError(
                f"String length must not exceed {rule.max_length}"
            )

        if rule.pattern and not rule.pattern.match(value):
            raise SearchValidationError("String does not match required pattern")

        if rule.allowed_values and value not in rule.allowed_values:
            raise SearchValidationError(f"Value must be one of: {rule.allowed_values}")

        return value

    def _validate_number(self, value: Any, rule: FilterRule) -> int | float:
        """Validate number field"""
        try:
            if isinstance(value, str):
                # Try to convert string to number
                value = float(value) if "." in value else int(value)
            elif not isinstance(value, (int, float)):
                raise SearchValidationError("Value must be a number")
        except (ValueError, TypeError) as e:
            raise SearchValidationError("Value must be a valid number") from e

        if rule.min_value is not None and value < rule.min_value:
            raise SearchValidationError(f"Value must be at least {rule.min_value}")

        if rule.max_value is not None and value > rule.max_value:
            raise SearchValidationError(f"Value must not exceed {rule.max_value}")

        return cast("int | float", value)

    def _validate_date(self, value: Any, rule: FilterRule) -> str:
        """Validate date field"""
        if not isinstance(value, str):
            raise SearchValidationError("Date value must be a string")

        # Basic ISO date validation
        iso_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}(T\d{2}:\d{2}:\d{2}(\.\d+)?Z?)?$")
        if not iso_pattern.match(value):
            raise SearchValidationError(
                "Date must be in ISO format (YYYY-MM-DD or YYYY-MM-DDTHH:MM:SSZ)",
            )

        return value

    def _validate_boolean(self, value: Any, rule: FilterRule) -> bool:
        """Validate boolean field"""
        if isinstance(value, str):
            if value.lower() in ("true", "1", "yes", "on"):
                return True
            if value.lower() in ("false", "0", "no", "off"):
                return False
            raise SearchValidationError("Invalid boolean value")
        if isinstance(value, (int, float)):
            return bool(value)
        if isinstance(value, bool):
            return value
        raise SearchValidationError("Value must be a boolean")

    def _validate_array(self, value: Any, rule: FilterRule) -> list[Any]:
        """Validate array field"""
        if not isinstance(value, list):
            raise SearchValidationError("Value must be an array")

        if rule.min_length and len(value) < rule.min_length:
            raise SearchValidationError(
                f"Array length must be at least {rule.min_length}"
            )

        if rule.max_length and len(value) > rule.max_length:
            raise SearchValidationError(
                f"Array length must not exceed {rule.max_length}"
            )

        if rule.array_item_type:
            # Validate each item in the array
            validated_items: list[Any] = []
            for item in value:
                if rule.array_item_type == FilterType.TEXT:
                    validated_items.append(
                        self._validate_text(item, FilterRule("", FilterType.TEXT)),
                    )
                elif rule.array_item_type == FilterType.NUMBER:
                    validated_items.append(
                        self._validate_number(item, FilterRule("", FilterType.NUMBER)),
                    )
                else:
                    validated_items.append(item)
            return validated_items

        return value

    def _validate_range(self, value: Any, rule: FilterRule) -> dict[str, Any]:
        """Validate range field"""
        if not isinstance(value, dict):
            raise SearchValidationError(
                "Range value must be an object with 'gte', 'gt', 'lte', 'lt' keys",
            )

        valid_keys = {"gte", "gt", "lte", "lt"}
        if not any(key in value for key in valid_keys):
            raise SearchValidationError(
                "Range must contain at least one of: gte, gt, lte, lt",
            )

        validated_range = {}
        for key, val in value.items():
            if key not in valid_keys:
                raise SearchValidationError(f"Invalid range key: {key}")

            # Validate the range value based on rule type
            if rule.min_value is not None or rule.max_value is not None:
                validated_val = self._validate_number(val, rule)
            else:
                validated_val = val

            validated_range[key] = validated_val

        return validated_range

    def _validate_exists(self, value: Any, rule: FilterRule) -> bool:
        """Validate exists field"""
        if not isinstance(value, bool):
            raise SearchValidationError("Exists value must be a boolean")
        return value


class FilterProcessor:
    """Processes and transforms filters"""

    def __init__(self, validator: FilterValidator | None = None):
        self.validator = validator

    def process_filters(
        self,
        filters: dict[str, Any],
        transform_rules: dict[str, Callable[[Any], Any]] | None = None,
    ) -> dict[str, Any]:
        """Process and transform filters"""
        # Validate if validator is provided
        if self.validator:
            filters = self.validator.validate_filters(filters)

        # Apply transformations
        if transform_rules:
            filters = self._apply_transformations(filters, transform_rules)

        return filters

    def _apply_transformations(
        self,
        filters: dict[str, Any],
        transform_rules: dict[str, Callable[[Any], Any]],
    ) -> dict[str, Any]:
        """Apply transformation rules to filters"""
        transformed = {}

        for field, value in filters.items():
            transformer = transform_rules.get(field)
            if transformer:
                try:
                    transformed[field] = transformer(value)
                except Exception as e:
                    raise SearchValidationError(
                        f"Filter transformation failed for '{field}': {e}",
                    ) from e
            else:
                transformed[field] = value

        return transformed


# Common filter transformation functions
def lowercase_filter(value: Any) -> str:
    """Convert string filter to lowercase"""
    if isinstance(value, str):
        return value.lower()
    return cast("str", value)


def trim_filter(value: Any) -> str:
    """Trim whitespace from string filter"""
    if isinstance(value, str):
        return value.strip()
    return cast("str", value)


def split_filter(separator: str = ",") -> Callable[[str], list[str]]:
    """Create a filter that splits string by separator"""

    def transform(value: Any) -> list[str]:
        if isinstance(value, str):
            return list(filter(None, map(str.strip, value.split(separator))))
        return cast("list[str]", value)

    return transform


def date_range_filter(value: Any) -> dict[str, str]:
    """Convert date range string to range object"""
    if isinstance(value, str):
        parts = value.split(" to ")
        if len(parts) == 2:
            return {"gte": parts[0], "lte": parts[1]}
        return {"gte": value, "lte": value}
    return cast("dict[str, str]", value)


__all__ = [
    "FilterProcessor",
    "FilterRule",
    "FilterType",
    "FilterValidator",
    "date_range_filter",
    "lowercase_filter",
    "split_filter",
    "trim_filter",
]

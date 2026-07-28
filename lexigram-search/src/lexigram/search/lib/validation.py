"""Validation Utilities"""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime
import re
from typing import Any

from lexigram.search.exceptions import SearchValidationError


class InputValidator:
    """Validates search input parameters"""

    def __init__(self) -> None:
        self._rules = {
            "query": self._validate_query,
            "filters": self._validate_filters,
            "limit": self._validate_limit,
            "offset": self._validate_offset,
            "sort": self._validate_sort,
            "fields": self._validate_fields,
        }

    def validate(self, params: dict[str, Any]) -> dict[str, Any]:
        """Validate search parameters"""
        validated = {}

        for key, value in params.items():
            if key in self._rules:
                validator = self._rules[key]
                validated[key] = validator(value, params)
            else:
                validated[key] = value

        return validated

    def _validate_query(self, value: Any, params: dict[str, Any]) -> str:
        """Validate search query"""
        if not isinstance(value, str):
            raise SearchValidationError("Query must be a string")

        query = value.strip()

        if not query:
            raise SearchValidationError("Query cannot be empty")

        if len(query) > 1000:
            raise SearchValidationError("Query too long (max 1000 characters)")

        # Check for potentially dangerous patterns
        dangerous_patterns = [
            r"<script",
            r"javascript:",
            r"on\w+\s*=",
        ]

        for pattern in dangerous_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                raise SearchValidationError(
                    "Query contains potentially dangerous content"
                )

        return query

    def _validate_filters(self, value: Any, params: dict[str, Any]) -> dict[str, Any]:
        """Validate search filters"""
        if not isinstance(value, dict):
            raise SearchValidationError("Filters must be a dictionary")

        validated = {}

        for key, val in value.items():
            # Validate filter key
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_\.]*$", key):
                raise SearchValidationError(f"Invalid filter key: {key}")

            # Basic value validation
            if val is None:
                continue

            validated[key] = val

        return validated

    def _validate_limit(self, value: Any, params: dict[str, Any]) -> int:
        """Validate result limit"""
        try:
            limit = int(value)
        except (TypeError, ValueError) as e:
            raise SearchValidationError("Limit must be a valid integer") from e

        if limit < 1:
            raise SearchValidationError("Limit must be greater than 0")

        if limit > 10000:
            raise SearchValidationError("Limit cannot exceed 10000")

        return limit

    def _validate_offset(self, value: Any, params: dict[str, Any]) -> int:
        """Validate result offset"""
        try:
            offset = int(value)
        except (TypeError, ValueError) as e:
            raise SearchValidationError("Offset must be a valid integer") from e

        if offset < 0:
            raise SearchValidationError("Offset cannot be negative")

        return offset

    def _validate_sort(
        self,
        value: Any,
        params: dict[str, Any],
    ) -> list[dict[str, Any]]:
        """Validate sort parameters"""
        if not isinstance(value, list):
            raise SearchValidationError("Sort must be a list")

        validated = []

        for item in value:
            if not isinstance(item, dict):
                raise SearchValidationError("Sort item must be a dictionary")

            if len(item) != 1:
                raise SearchValidationError("Sort item must have exactly one field")

            field, config = next(iter(item.items()))

            # Validate field name
            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_\.]*$", field):
                raise SearchValidationError(f"Invalid sort field: {field}")

            # Validate sort config
            if not isinstance(config, dict):
                raise SearchValidationError("Sort configuration must be a dictionary")

            order = config.get("order", "asc")
            if order not in ("asc", "desc"):
                raise SearchValidationError(f"Invalid sort order: {order}")

            validated.append({field: config})

        return validated

    def _validate_fields(self, value: Any, params: dict[str, Any]) -> list[str]:
        """Validate field selection"""
        if not isinstance(value, list):
            raise SearchValidationError("Fields must be a list")

        validated = []

        for field in value:
            if not isinstance(field, str):
                raise SearchValidationError("Field must be a string")

            if not re.match(r"^[a-zA-Z_][a-zA-Z0-9_\.]*$", field):
                raise SearchValidationError(f"Invalid field name: {field}")

            validated.append(field)

        return validated


class DocumentValidator:
    """Validates documents before indexing"""

    def __init__(self, schema: dict[str, Any] | None = None):
        self.schema = schema or {}

    def validate_document(self, document: dict[str, Any]) -> dict[str, Any]:
        """Validate a document against schema"""
        if not isinstance(document, dict):
            raise SearchValidationError("Document must be a dictionary")

        validated = {}

        # Check required fields
        for field, field_schema in self.schema.items():
            if field_schema.get("required", False):
                if field not in document:
                    raise SearchValidationError(f"Required field missing: {field}")

        # Validate each field
        for key, value in document.items():
            field_schema = self.schema.get(key, {})
            validated[key] = self._validate_field(key, value, field_schema)

        return validated

    def _validate_field(self, field: str, value: Any, schema: dict[str, Any]) -> Any:
        """Validate a single field"""
        field_type = schema.get("type")

        if field_type == "string":
            return self._validate_string_field(value, schema)
        if field_type == "integer":
            return self._validate_integer_field(value, schema)
        if field_type == "number":
            return self._validate_number_field(value, schema)
        if field_type == "boolean":
            return self._validate_boolean_field(value, schema)
        if field_type == "date":
            return self._validate_date_field(value, schema)
        if field_type == "array":
            return self._validate_array_field(value, schema)
        # No type validation
        return value

    def _validate_string_field(self, value: Any, schema: dict[str, Any]) -> str:
        """Validate string field"""
        if not isinstance(value, str):
            raise SearchValidationError("Field must be a string")

        min_length = schema.get("minLength")
        max_length = schema.get("maxLength")
        pattern = schema.get("pattern")

        if min_length and len(value) < min_length:
            raise SearchValidationError(f"String too short (min {min_length})")

        if max_length and len(value) > max_length:
            raise SearchValidationError(f"String too long (max {max_length})")

        if pattern and not re.match(pattern, value):
            raise SearchValidationError(f"String does not match pattern: {pattern}")

        return value

    def _validate_integer_field(self, value: Any, schema: dict[str, Any]) -> int:
        """Validate integer field"""
        try:
            int_value = int(value)
        except (TypeError, ValueError) as e:
            raise SearchValidationError("Field must be a valid integer") from e

        minimum = schema.get("minimum")
        maximum = schema.get("maximum")

        if minimum is not None and int_value < minimum:
            raise SearchValidationError(f"Value too small (min {minimum})")

        if maximum is not None and int_value > maximum:
            raise SearchValidationError(f"Value too large (max {maximum})")

        return int_value

    def _validate_number_field(self, value: Any, schema: dict[str, Any]) -> int | float:
        """Validate number field"""
        try:
            num_value = float(value)
        except (TypeError, ValueError) as e:
            raise SearchValidationError("Field must be a valid number") from e

        minimum = schema.get("minimum")
        maximum = schema.get("maximum")

        if minimum is not None and num_value < minimum:
            raise SearchValidationError(f"Value too small (min {minimum})")

        if maximum is not None and num_value > maximum:
            raise SearchValidationError(f"Value too large (max {maximum})")

        return num_value

    def _validate_boolean_field(self, value: Any, schema: dict[str, Any]) -> bool:
        """Validate boolean field"""
        if isinstance(value, str):
            if value.lower() in ("true", "1", "yes", "on"):
                return True
            if value.lower() in ("false", "0", "no", "off"):
                return False

        return bool(value)

    def _validate_date_field(self, value: Any, schema: dict[str, Any]) -> str:
        """Validate date field"""
        if isinstance(value, datetime):
            return value.isoformat()
        if isinstance(value, str):
            # Try to parse as ISO date
            try:
                datetime.fromisoformat(value.replace("Z", "+00:00"))
                return value
            except ValueError as e:
                raise SearchValidationError("Invalid date format") from e
        else:
            raise SearchValidationError("Date field must be a string or datetime")

    def _validate_array_field(self, value: Any, schema: dict[str, Any]) -> list[Any]:
        """Validate array field"""
        if not isinstance(value, list):
            raise SearchValidationError("Field must be an array")

        min_items = schema.get("minItems")
        max_items = schema.get("maxItems")

        if min_items and len(value) < min_items:
            raise SearchValidationError(f"Array too small (min {min_items} items)")

        if max_items and len(value) > max_items:
            raise SearchValidationError(f"Array too large (max {max_items} items)")

        # Validate item type if specified
        item_schema = schema.get("items", {})
        if item_schema:
            validated_items = []
            for item in value:
                validated_items.append(self._validate_field("item", item, item_schema))
            return validated_items

        return value


class ValidationChain:
    """Chain multiple validators together"""

    def __init__(self, validators: list[Callable] | None = None):
        self.validators = validators or []

    def add_validator(self, validator: Callable) -> None:
        """Add a validator to the chain"""
        self.validators.append(validator)

    async def validate(self, data: Any) -> Any:
        """Run all validators in sequence"""
        result = data

        for validator in self.validators:
            result = await validator(result)

        return result


__all__ = ["DocumentValidator", "InputValidator", "ValidationChain"]

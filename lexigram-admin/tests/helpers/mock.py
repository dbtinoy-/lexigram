import datetime
import random
from typing import Any

from lexigram.admin.resources.base import Resource
from lexigram.admin.ui.columns import (
    BadgeColumn,
    BooleanColumn,
    Column,
    CurrencyColumn,
    DateColumn,
    ImageColumn,
    TextColumn,
)

try:
    from faker import Faker

    fake = Faker()
except ImportError:
    fake = None


class MockDataGenerator:
    """
    Generates mock data for a Resource based on its column configuration.

    Usage:
        generator = MockDataGenerator(UserResource)
        data = generator.generate(10)
    """

    def __init__(self, resource_cls: type[Resource]):
        self.resource_cls = resource_cls
        self.config = resource_cls.get_table_config()

    def generate(self, count: int = 10) -> list[dict[str, Any]]:
        """Generate a list of mock records."""
        return [self._generate_record(i) for i in range(count)]

    def _generate_record(self, index: int) -> dict[str, Any]:
        record = {}
        for col in self.config.columns:
            value = self._generate_value(col, index)
            self._set_nested(record, col.name, value)

        # Always ensure ID exists if not explicitly in columns?
        if "id" not in record:
            record["id"] = index + 1

        return record

    def _set_nested(self, d: dict, key: str, value: Any):
        """Set value for potentially nested key 'user.name'."""
        parts = key.split(".")
        target = d
        for part in parts[:-1]:
            if part not in target:
                target[part] = {}
            target = target[part]
        target[parts[-1]] = value

    def _generate_value(self, col: Column, index: int) -> Any:
        name_lower = col.name.lower()

        # 1. Use Faker if available and name matches common patterns
        if fake:
            if "email" in name_lower:
                return fake.email()
            if "name" in name_lower:
                return fake.name()
            if "address" in name_lower:
                return fake.address()
            if "phone" in name_lower:
                return fake.phone_number()
            if "company" in name_lower:
                return fake.company()
            if "bio" in name_lower or "desc" in name_lower:
                return fake.sentence()

        # 2. Type-based Fallback
        if isinstance(col, TextColumn):
            if "id" in name_lower:
                return index + 1
            if fake:
                return fake.word().title()
            return f"{col.name}_{index}"

        if isinstance(col, DateColumn):
            if fake:
                return fake.date_time_between(start_date="-1y", end_date="now")
            return datetime.datetime.now() - datetime.timedelta(
                days=random.randint(0, 365),
            )

        if isinstance(col, BooleanColumn):
            return random.choice([True, False])

        if isinstance(col, BadgeColumn):
            if hasattr(col, "_colors") and col._colors:
                return random.choice(list(col._colors.keys()))
            return random.choice(["active", "inactive", "pending"])

        if isinstance(col, CurrencyColumn):
            return round(random.uniform(10.0, 1000.0), 2)

        if isinstance(col, ImageColumn):
            if fake:
                return fake.image_url()
            return f"https://via.placeholder.com/150?text={col.name}"

        return f"Mock {col.name}"


__all__ = ["MockDataGenerator"]

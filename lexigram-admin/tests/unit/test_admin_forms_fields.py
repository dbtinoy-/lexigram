"""Tests for form field types."""

import pytest

from lexigram.admin.forms.fields import FieldType


class TestFieldType:
    """Tests for FieldType enum."""

    def test_field_type_values(self) -> None:
        """Test FieldType enum values."""
        assert FieldType.TEXT.value == "text"
        assert FieldType.NUMBER.value == "number"
        assert FieldType.EMAIL.value == "email"
        assert FieldType.PASSWORD.value == "password"
        assert FieldType.CHECKBOX.value == "checkbox"
        assert FieldType.SELECT.value == "select"
        assert FieldType.MULTI_SELECT.value == "multi_select"
        assert FieldType.DATE.value == "date"
        assert FieldType.DATETIME.value == "datetime"
        assert FieldType.TEXTAREA.value == "textarea"
        assert FieldType.FILE.value == "file"
        assert FieldType.IMAGE.value == "image"

    def test_field_type_members(self) -> None:
        """Test FieldType has expected members."""
        members = list(FieldType)
        assert len(members) >= 12

    def test_field_type_is_str_enum(self) -> None:
        """Test FieldType is a StrEnum."""
        assert isinstance(FieldType.TEXT, str)
        assert FieldType.TEXT == "text"

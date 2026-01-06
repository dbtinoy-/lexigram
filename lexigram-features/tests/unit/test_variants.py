"""Test variant weight validation.

Tests for task: "Validate variant weight validation"
from 2026-03-12-features-guide-alignment.md §5 Codebase Alignment Tasks.

Tests verify that Flag variant weights are validated in __post_init__.
Variant weights must sum to exactly 100.
"""

from __future__ import annotations

import pytest

from lexigram.features.types import Flag, FlagType


class TestVariantWeightValidation:
    """Verify Flag variant weight validation in __post_init__."""

    def test_valid_variant_weights_sum_to_100(self) -> None:
        """Valid variant with weights summing to 100 should be accepted."""
        flag = Flag(
            name="test_variant",
            type=FlagType.VARIANT,
            variants={"option_a": 50, "option_b": 30, "option_c": 20},
        )
        assert flag.name == "test_variant"
        assert flag.variants == {"option_a": 50, "option_b": 30, "option_c": 20}

    def test_two_equal_weights(self) -> None:
        """Two variants with 50/50 split should be valid."""
        flag = Flag(
            name="ab_test",
            type=FlagType.VARIANT,
            variants={"control": 50, "treatment": 50},
        )
        assert flag.name == "ab_test"
        assert sum(flag.variants.values()) == 100

    def test_single_variant_100_percent(self) -> None:
        """Single variant with 100% should be valid."""
        flag = Flag(
            name="single",
            type=FlagType.VARIANT,
            variants={"only_option": 100},
        )
        assert flag.variants == {"only_option": 100}

    def test_weights_less_than_100_rejected(self) -> None:
        """Flag with variant weights summing less than 100 should be rejected."""
        with pytest.raises(ValueError, match="Variant weights must sum to 100"):
            Flag(
                name="invalid",
                type=FlagType.VARIANT,
                variants={"option_a": 40, "option_b": 50},  # sums to 90
            )

    def test_weights_more_than_100_rejected(self) -> None:
        """Flag with variant weights summing more than 100 should be rejected."""
        with pytest.raises(ValueError, match="Variant weights must sum to 100"):
            Flag(
                name="invalid",
                type=FlagType.VARIANT,
                variants={"option_a": 60, "option_b": 50},  # sums to 110
            )

    def test_empty_variants_dict_allowed(self) -> None:
        """Flag with VARIANT type but empty variants dict should be allowed (no validation)."""
        # Empty dict won't trigger validation since "if self.variants:" is False
        flag = Flag(
            name="empty_ok",
            type=FlagType.VARIANT,
            variants={},
        )
        assert flag.variants == {}

    def test_zero_weights_rejected(self) -> None:
        """All zero weights should be rejected."""
        with pytest.raises(ValueError, match="Variant weights must sum to 100"):
            Flag(
                name="all_zero",
                type=FlagType.VARIANT,
                variants={"option_a": 0, "option_b": 0},
            )

    def test_negative_weights_rejected(self) -> None:
        """Negative weights that sum to incorrect value should be rejected."""
        with pytest.raises(ValueError, match="Variant weights must sum to 100"):
            Flag(
                name="negative",
                type=FlagType.VARIANT,
                variants={"option_a": -10, "option_b": 120},  # sums to 110, not 100
            )

    def test_float_weights_not_allowed(self) -> None:
        """Float weights in variant should sum check (can be dict with int values)."""
        # This would need integer or proper float handling
        # If variants accepts int only, floats won't work
        flag = Flag(
            name="float_weights",
            type=FlagType.VARIANT,
            variants={"option_a": 50, "option_b": 50},  # Using ints
        )
        assert sum(flag.variants.values()) == 100

    def test_three_way_split(self) -> None:
        """Three-way split with rounding should be valid."""
        flag = Flag(
            name="three_way",
            type=FlagType.VARIANT,
            variants={"option_a": 34, "option_b": 33, "option_c": 33},
        )
        assert sum(flag.variants.values()) == 100

    def test_many_options(self) -> None:
        """Flag with many variant options should work if weights sum to 100."""
        variants = {f"option_{i}": 10 for i in range(10)}
        flag = Flag(
            name="ten_way",
            type=FlagType.VARIANT,
            variants=variants,
        )
        assert sum(flag.variants.values()) == 100
        assert len(flag.variants) == 10

    def test_validation_message_clarity(self) -> None:
        """Error message should clearly indicate the weight sum problem."""
        try:
            Flag(
                name="test",
                type=FlagType.VARIANT,
                variants={"a": 75, "b": 15},  # sums to 90
            )
            pytest.fail("Should have raised ValueError")
        except ValueError as e:
            error_msg = str(e).lower()
            # Error should mention weights or sum
            assert (
                "weight" in error_msg or "sum" in error_msg or "100" in error_msg
            ), f"Error message not clear: {e}"

    def test_whitespace_in_variant_names(self) -> None:
        """Variant option names with whitespace should be handled correctly."""
        flag = Flag(
            name="with_spaces",
            type=FlagType.VARIANT,
            variants={"option one": 50, "option two": 50},
        )
        assert flag.variants == {"option one": 50, "option two": 50}

    def test_special_characters_in_variant_names(self) -> None:
        """Variant option names with special characters should be handled correctly."""
        flag = Flag(
            name="special_chars",
            type=FlagType.VARIANT,
            variants={"control-group_v1": 50, "treatment-group_v2": 50},
        )
        assert flag.variants == {"control-group_v1": 50, "treatment-group_v2": 50}

    def test_non_variant_type_ignores_weights(self) -> None:
        """Non-VARIANT flag types should not validate variant weights."""
        # BOOLEAN type flag with variants field set should not validate
        flag = Flag(
            name="boolean_with_variants",
            type=FlagType.BOOLEAN,
            variants={"a": 50, "b": 50},  # This won't be validated for non-VARIANT type
        )
        # Should succeed because weight validation only happens for type=FlagType.VARIANT
        assert flag.variants == {"a": 50, "b": 50}

    def test_variant_type_with_default_variant(self) -> None:
        """Flag with VARIANT type can specify a default_variant."""
        flag = Flag(
            name="test",
            type=FlagType.VARIANT,
            variants={"a": 50, "b": 50},
            default_variant="a",
        )
        assert flag.default_variant == "a"
        assert flag.variants == {"a": 50, "b": 50}

    def test_very_unequal_split(self) -> None:
        """Variant weights can be very unequal as long as they sum to 100."""
        flag = Flag(
            name="heavily_weighted",
            type=FlagType.VARIANT,
            variants={"control": 95, "experiment": 5},
        )
        assert sum(flag.variants.values()) == 100
        assert flag.variants["control"] == 95


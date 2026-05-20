"""Tests for config node validation and spec metadata."""

from __future__ import annotations

from typing import Literal

import pytest

from lexigram.admin.settings.panel.nodes import (
    BooleanNode,
    ColorNode,
    EnumNode,
    IntNode,
    PydanticConfigSpec,
    StringNode,
)
from lexigram.domain import DomainModel
from lexigram.validation import Field


class ColorModel(DomainModel):
    """Test model with mixed field types."""

    name: str = Field(default="x", title="Name")
    count: int = Field(default=3, title="Count")
    enabled: bool = Field(default=True, title="Enabled")
    mode: Literal["a", "b"] = Field(default="a", title="Mode")
    color: str = Field(default="#123456", title="Color")


class MixedSpec(PydanticConfigSpec):
    """Spec bound to ColorModel."""

    namespace = "test.mixed"
    model = ColorModel
    node_overrides = {"color": ColorNode}


class TestColorNode:
    """Tests for ColorNode hex validation."""

    def test_accepts_valid_hex(self) -> None:
        node = ColorNode(label="Color", default="#123456")
        assert node.validate("#ABCDEF") == "#ABCDEF"

    def test_rejects_invalid_hex_falls_back_to_default(self) -> None:
        node = ColorNode(label="Color", default="#123456")
        assert node.validate("not-a-color") == "#123456"

    def test_rejects_short_hex(self) -> None:
        node = ColorNode(label="Color", default="#123456")
        assert node.validate("#fff") == "#123456"


class TestPydanticConfigSpecNodes:
    """Tests for dynamic node derivation from models."""

    def test_nodes_derived_from_model(self) -> None:
        nodes = MixedSpec.get_nodes()
        assert set(nodes) == {"name", "count", "enabled", "mode", "color"}
        assert isinstance(nodes["name"], StringNode)
        assert isinstance(nodes["count"], IntNode)
        assert isinstance(nodes["enabled"], BooleanNode)
        assert isinstance(nodes["mode"], EnumNode)
        assert isinstance(nodes["color"], ColorNode)

    def test_enum_node_has_options(self) -> None:
        nodes = MixedSpec.get_nodes()
        mode = nodes["mode"]
        assert isinstance(mode, EnumNode)
        assert mode.options == ["a", "b"]

    def test_labels_and_defaults_from_field_metadata(self) -> None:
        nodes = MixedSpec.get_nodes()
        assert nodes["count"].label == "Count"
        assert nodes["count"].default == 3
        assert nodes["count"].validate("7") == 7

    def test_literal_default_falls_back_to_first_option(self) -> None:
        nodes = MixedSpec.get_nodes()
        assert nodes["mode"].default == "a"


class TestSpecMetadata:
    """Tests for spec description and permissions metadata."""

    def test_spec_description_defaults_empty(self) -> None:
        assert MixedSpec.description == ""

    def test_spec_required_permissions_defaults_empty(self) -> None:
        assert MixedSpec.required_permissions == frozenset()

    def test_to_dict_includes_description(self) -> None:
        d = MixedSpec.to_dict()
        assert "description" in d
        assert "namespace" in d
        assert "nodes" in d


@pytest.mark.asyncio
async def test_get_nodes_empty_when_no_model() -> None:
    class NoModelSpec(PydanticConfigSpec):
        namespace = "test.nomodel"

    assert NoModelSpec.get_nodes() == {}

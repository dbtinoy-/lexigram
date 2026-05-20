"""Tests for config node validation and spec metadata."""

from __future__ import annotations

from typing import Literal

import pytest

from lexigram.admin.settings.panel.nodes import (
    BooleanNode,
    ColorNode,
    ConfigSpec,
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
    mode: Literal["a", "b"] = Field(default="zzz", title="Mode")
    color: str = Field(default="#123456", title="Color")


class MixedSpec(PydanticConfigSpec):
    """Spec bound to ColorModel."""

    namespace = "test.mixed"
    model = ColorModel
    node_overrides = {"color": ColorNode}


class OverrideModel(DomainModel):
    """Model whose int field is overridden."""

    count: int = Field(default=3, title="Count")


class OverrideSpec(PydanticConfigSpec):
    """Spec overriding an int field with ColorNode."""

    namespace = "test.override"
    model = OverrideModel
    node_overrides = {"count": ColorNode}


class IntLiteralModel(DomainModel):
    """Model with non-string Literal."""

    retries: Literal[1, 2, 3] = Field(1, title="Retries")


class IntLiteralSpec(PydanticConfigSpec):
    """Spec bound to IntLiteralModel."""

    namespace = "test.intliteral"
    model = IntLiteralModel


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

    def test_node_override_wins_over_type_mapping(self) -> None:
        nodes = OverrideSpec.get_nodes()
        assert isinstance(nodes["count"], ColorNode)

    def test_enum_options_coerced_to_strings(self) -> None:
        nodes = IntLiteralSpec.get_nodes()
        assert isinstance(nodes["retries"], EnumNode)
        assert nodes["retries"].validate(2) == "2"

    def test_enum_node_instance_override(self) -> None:
        class InstOverrideSpec(PydanticConfigSpec):
            """Spec with an EnumNode instance override."""

            namespace = "test.instoverride"
            model = ColorModel
            node_overrides = {"mode": EnumNode(options=["x", "y"], label="Mode")}

        nodes = InstOverrideSpec.get_nodes()
        assert isinstance(nodes["mode"], EnumNode)
        assert nodes["mode"].options == ["x", "y"]
        assert nodes["mode"].label == "Mode"

    def test_required_literal_has_no_default(self) -> None:
        class ReqLiteralModel(DomainModel):
            """Model with required Literal."""

            mode: Literal["a", "b"] = Field(..., title="Mode")

        class ReqLiteralSpec(PydanticConfigSpec):
            """Spec bound to ReqLiteralModel."""

            namespace = "test.reqliteral"
            model = ReqLiteralModel

        nodes = ReqLiteralSpec.get_nodes()
        assert nodes["mode"].required is True
        assert nodes["mode"].default is None

    def test_int_node_enforces_ge_le(self) -> None:
        class BoundedModel(DomainModel):
            """Model with bounded int field."""

            ttl: int = Field(60, ge=0, title="TTL")

        class BoundedSpec(PydanticConfigSpec):
            """Spec bound to BoundedModel."""

            namespace = "test.bounded"
            model = BoundedModel

        nodes = BoundedSpec.get_nodes()
        assert nodes["ttl"].validate(-5) == 60
        assert nodes["ttl"].validate(120) == 120

    def test_plain_pydantic_model_binding_raises(self) -> None:
        from pydantic import BaseModel as PydanticBaseModel

        class PlainModel(PydanticBaseModel):
            """Plain pydantic model."""

            name: str

        class PlainSpec(PydanticConfigSpec):
            """Spec bound to a non-dataclass model."""

            namespace = "test.plain"
            model = PlainModel

        with pytest.raises(TypeError):
            PlainSpec.get_nodes()

    def test_static_node_inheritance(self) -> None:
        class ParentSpec(ConfigSpec):
            """Parent static-node spec."""

            namespace = "test.parent"
            a = StringNode(label="A", default=None)

        class ChildSpec(ParentSpec):
            """Child static-node spec."""

            namespace = "test.child"
            b = StringNode(label="B", default=None)

        assert set(ChildSpec.get_nodes()) == {"a", "b"}


class TestEnumNode:
    """Tests for EnumNode validate behavior."""

    def test_enum_validate_string_and_dict_options(self) -> None:
        node = EnumNode(options=["red", "blue"], default="red", label="Color")
        assert node.validate("blue") == "blue"
        assert node.validate("green") == "red"

        dict_node = EnumNode(
            options={"on": "Enabled", "off": "Disabled"},
            default="on",
            label="Switch",
        )
        assert dict_node.validate("on") == "on"
        assert dict_node.validate("nope") == "on"


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


class TestOptionalFields:
    """Tests for optional field handling."""

    def test_field_with_default_none_is_optional(self) -> None:
        class OptionalModel(DomainModel):
            """Model with an explicitly optional field."""

            note: str | None = Field(default=None, title="Note")

        class OptionalSpec(PydanticConfigSpec):
            """Spec bound to OptionalModel."""

            namespace = "test.optional"
            model = OptionalModel

        nodes = OptionalSpec.get_nodes()
        assert nodes["note"].required is False
        assert nodes["note"].default is None


def test_get_nodes_empty_when_no_model() -> None:
    class NoModelSpec(PydanticConfigSpec):
        namespace = "test.nomodel"

    assert NoModelSpec.get_nodes() == {}

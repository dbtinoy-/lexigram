"""Tests for the node_generators module."""

from __future__ import annotations

import pytest

from lexigram_builder.gen.node_generators import (
    ENTITY_ATTACHED,
    VERB_SPECS,
    VerbSpec,
    entity_attached_extra_kwargs,
    get_verb_spec,
)
from lexigram_builder.graph.palette import (
    KIND_AUTH,
    KIND_CONTRACT,
    KIND_ENTITY,
    KIND_FEATURE_FLAG,
    KIND_JOB,
    KIND_RATE_LIMIT,
    KIND_ROLE,
    KIND_ROUTE,
    KIND_SERVICE,
)


class TestVerbSpecs:
    """Tests for VERB_SPECS."""

    def test_feature_flag_spec_exists(self) -> None:
        spec = get_verb_spec(KIND_FEATURE_FLAG)
        assert spec is not None
        assert spec.generator_name == "feature_flag"
        assert spec.package == "features"
        assert spec.output_dir == "src/app/features"

    def test_auth_spec_exists(self) -> None:
        spec = get_verb_spec(KIND_AUTH)
        assert spec is not None
        assert spec.generator_name == "auth_guard"
        assert spec.package == "auth"
        assert spec.output_dir == "src/app/guards"

    def test_role_spec_exists(self) -> None:
        spec = get_verb_spec(KIND_ROLE)
        assert spec is not None
        assert spec.generator_name == "guard"
        assert spec.package == "auth"

    def test_rate_limit_spec_exists(self) -> None:
        spec = get_verb_spec(KIND_RATE_LIMIT)
        assert spec is not None
        assert spec.generator_name == "rate_limit"
        assert spec.package == "auth"

    def test_contract_spec_exists(self) -> None:
        spec = get_verb_spec(KIND_CONTRACT)
        assert spec is not None
        assert spec.generator_name == "contract"
        assert spec.package == "web"
        assert spec.output_dir == "src/app/contracts"

    def test_unknown_kind_returns_none(self) -> None:
        assert get_verb_spec("nonexistent") is None

    def test_all_specs_have_required_fields(self) -> None:
        for spec in VERB_SPECS:
            assert spec.kind, f"Spec has empty kind"
            assert spec.generator_name, f"{spec.kind} has empty generator_name"
            assert spec.package, f"{spec.kind} has empty package"
            assert spec.output_dir, f"{spec.kind} has empty output_dir"


class TestEntityAttached:
    """Tests for ENTITY_ATTACHED and entity_attached_extra_kwargs."""

    def test_entity_attached_kinds(self) -> None:
        assert KIND_SERVICE in ENTITY_ATTACHED
        assert KIND_JOB in ENTITY_ATTACHED

    def test_service_extra_kwargs(self) -> None:
        kwargs = entity_attached_extra_kwargs(
            KIND_SERVICE, "user", "name:str, email:str"
        )
        assert kwargs["entity"] == "user"
        assert kwargs["fields"] == "name:str, email:str"

    def test_job_extra_kwargs(self) -> None:
        kwargs = entity_attached_extra_kwargs(KIND_JOB, "order", "")
        assert kwargs["entity"] == "order"

    def test_unknown_kind_returns_empty(self) -> None:
        kwargs = entity_attached_extra_kwargs("unknown", "x", "")
        assert kwargs == {}

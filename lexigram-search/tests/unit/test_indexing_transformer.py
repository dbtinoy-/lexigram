"""Tests for document transformation modules."""
from __future__ import annotations

from datetime import datetime

import pytest

from lexigram.search.backends.translate import TranslatedQuery
from lexigram.search.exceptions import TransformationError
from lexigram.search.indexing.transformer import (
    DefaultDocumentTransformer,
    DocumentTransformer,
    FieldMapper,
    TransformationPipeline,
    TransformationRule,
    ValueTransformer,
    extract_keywords,
    format_date,
    join_list,
    lowercase_text,
    normalize_whitespace,
    numeric_range,
    split_text,
    trim_text,
)


class TestTransformationRule:
    """Tests for TransformationRule dataclass."""

    def test_create_rule(self) -> None:
        """Verify TransformationRule creation."""
        rule = TransformationRule(
            field="name",
            transform_func=str.upper,
        )
        assert rule.field == "name"
        assert rule.transform_func("hello") == "HELLO"
        assert rule.condition is None
        assert rule.required is False

    def test_rule_with_condition(self) -> None:
        """Verify TransformationRule with condition."""
        rule = TransformationRule(
            field="status",
            transform_func=str.lower,
            condition=lambda d: d.get("type") == "user",
        )
        assert rule.condition({"type": "user"}) is True
        assert rule.condition({"type": "admin"}) is False

    def test_rule_required(self) -> None:
        """Verify TransformationRule required flag."""
        rule = TransformationRule(
            field="email",
            transform_func=str.lower,
            required=True,
        )
        assert rule.required is True


class TestDefaultDocumentTransformer:
    """Tests for DefaultDocumentTransformer."""

    @pytest.fixture
    def transformer(self) -> DefaultDocumentTransformer:
        return DefaultDocumentTransformer()

    def test_init_with_pipelines(self) -> None:
        """Verify transformer accepts pipelines."""
        pipeline = TransformationPipeline(name="test")
        transformer = DefaultDocumentTransformer(pipelines=[pipeline])
        assert len(transformer.pipelines) == 1

    def test_add_pipeline(self, transformer: DefaultDocumentTransformer) -> None:
        """Verify add_pipeline adds a pipeline."""
        pipeline = TransformationPipeline(name="test")
        transformer.add_pipeline(pipeline)
        assert len(transformer.pipelines) == 1

    @pytest.mark.asyncio
    async def test_to_target_no_pipelines(self, transformer: DefaultDocumentTransformer) -> None:
        """Verify to_target returns a copy with no pipelines."""
        doc = {"name": "test", "value": 42}
        result = await transformer.to_target(doc)
        assert result == doc
        assert result is not doc  # Should be a copy

    @pytest.mark.asyncio
    async def test_to_target_with_simple_pipeline(self, transformer: DefaultDocumentTransformer) -> None:
        """Verify to_target applies a simple pipeline."""
        pipeline = TransformationPipeline(
            name="lowercase",
            rules=[
                TransformationRule(
                    field="name",
                    transform_func=lambda v: v.lower() if v else v,
                ),
            ],
        )
        transformer.add_pipeline(pipeline)
        result = await transformer.to_target({"name": "HELLO"})
        assert result["name"] == "hello"

    @pytest.mark.asyncio
    async def test_to_target_with_conditional_rule(self, transformer: DefaultDocumentTransformer) -> None:
        """Verify conditional rule is only applied when condition met."""
        pipeline = TransformationPipeline(
            name="conditional",
            rules=[
                TransformationRule(
                    field="name",
                    transform_func=lambda v: v.upper(),
                    condition=lambda d: d.get("active") is True,
                ),
            ],
        )
        transformer.add_pipeline(pipeline)

        result_active = await transformer.to_target({"name": "hello", "active": True})
        assert result_active["name"] == "HELLO"

        result_inactive = await transformer.to_target({"name": "hello", "active": False})
        assert result_inactive["name"] == "hello"

    @pytest.mark.asyncio
    async def test_to_target_required_field_raises(self, transformer: DefaultDocumentTransformer) -> None:
        """Verify required field failure raises TransformationError."""
        pipeline = TransformationPipeline(
            name="required",
            rules=[
                TransformationRule(
                    field="email",
                    transform_func=lambda v: v.lower(),
                    required=True,
                ),
            ],
        )
        transformer.add_pipeline(pipeline)

        with pytest.raises(TransformationError):
            await transformer.to_target({"name": "test"})

    @pytest.mark.asyncio
    async def test_to_target_with_pre_transform(self, transformer: DefaultDocumentTransformer) -> None:
        """Verify pre_transform is called."""
        pipeline = TransformationPipeline(
            name="pre",
            pre_transform=lambda d: {**d, "_pre": True},
        )
        transformer.add_pipeline(pipeline)
        result = await transformer.to_target({"name": "test"})
        assert result["_pre"] is True

    @pytest.mark.asyncio
    async def test_to_target_with_post_transform(self, transformer: DefaultDocumentTransformer) -> None:
        """Verify post_transform is called."""
        pipeline = TransformationPipeline(
            name="post",
            post_transform=lambda d: {**d, "_post": True},
        )
        transformer.add_pipeline(pipeline)
        result = await transformer.to_target({"name": "test"})
        assert result["_post"] is True

    @pytest.mark.asyncio
    async def test_to_target_batch(self, transformer: DefaultDocumentTransformer) -> None:
        """Verify to_target_batch transforms multiple documents."""
        docs = [{"name": "hello"}, {"name": "world"}]
        results = await transformer.to_target_batch(docs)
        assert len(results) == 2
        assert results[0]["name"] == "hello"
        assert results[1]["name"] == "world"

    @pytest.mark.asyncio
    async def test_to_target_batch_with_pipeline(self, transformer: DefaultDocumentTransformer) -> None:
        """Verify to_target_batch applies pipeline to all docs."""
        pipeline = TransformationPipeline(
            name="uppercase",
            rules=[
                TransformationRule(
                    field="name",
                    transform_func=lambda v: v.upper() if v else v,
                ),
            ],
        )
        transformer.add_pipeline(pipeline)
        results = await transformer.to_target_batch([{"name": "hello"}, {"name": "world"}])
        assert results[0]["name"] == "HELLO"
        assert results[1]["name"] == "WORLD"

    @pytest.mark.asyncio
    async def test_pipeline_exception_raises_transformation_error(self, transformer: DefaultDocumentTransformer) -> None:
        """Verify pipeline exception is wrapped in TransformationError."""
        pipeline = TransformationPipeline(
            name="failing",
            pre_transform=lambda d: (_ for _ in ()).throw(RuntimeError("pre_transform failed")),
        )
        transformer.add_pipeline(pipeline)

        with pytest.raises(TransformationError, match="Pipeline 'failing' failed"):
            await transformer.to_target({"value": 1})

    @pytest.mark.asyncio
    async def test_optional_field_error_does_not_raise(self, transformer: DefaultDocumentTransformer) -> None:
        """Verify non-required field error is silently handled."""
        pipeline = TransformationPipeline(
            name="optional",
            rules=[
                TransformationRule(
                    field="value",
                    transform_func=lambda v: 1 / 0,
                    required=False,
                ),
            ],
        )
        transformer.add_pipeline(pipeline)
        result = await transformer.to_target({"name": "test"})
        assert result["name"] == "test"


class TestFieldMapper:
    """Tests for FieldMapper."""

    @pytest.fixture
    def mapper(self) -> FieldMapper:
        return FieldMapper(mappings={"old_name": "new_name", "title": "heading"})

    def test_init_empty(self) -> None:
        """Verify FieldMapper can be initialized empty."""
        mapper = FieldMapper()
        assert mapper.mappings == {}

    def test_init_with_mappings(self) -> None:
        """Verify mappings are accepted."""
        mapper = FieldMapper({"a": "b"})
        assert mapper.mappings["a"] == "b"

    def test_add_mapping(self) -> None:
        """Verify add_mapping adds a mapping."""
        mapper = FieldMapper()
        mapper.add_mapping("from_field", "to_field")
        assert mapper.mappings["from_field"] == "to_field"

    @pytest.mark.asyncio
    async def test_transform_renames_fields(self, mapper: FieldMapper) -> None:
        """Verify transform renames fields per mappings."""
        result = await mapper.transform({"old_name": "value", "title": "hello", "keep": "stay"})
        assert "new_name" in result
        assert "old_name" not in result
        assert result["new_name"] == "value"
        assert result["heading"] == "hello"
        assert result["keep"] == "stay"

    @pytest.mark.asyncio
    async def test_transform_no_mappings(self) -> None:
        """Verify transform with no mappings returns identical doc."""
        mapper = FieldMapper()
        result = await mapper.transform({"a": 1, "b": 2})
        assert result == {"a": 1, "b": 2}


class TestValueTransformer:
    """Tests for ValueTransformer."""

    @pytest.fixture
    def transformer(self) -> ValueTransformer:
        return ValueTransformer(transformers={
            "name": str.upper,
            "price": lambda v: v * 2,
        })

    def test_init_empty(self) -> None:
        """Verify ValueTransformer can be empty."""
        vt = ValueTransformer()
        assert vt.transformers == {}

    def test_add_transformer(self) -> None:
        """Verify add_transformer adds a transformer."""
        vt = ValueTransformer()
        vt.add_transformer("field", str.lower)
        assert "field" in vt.transformers

    @pytest.mark.asyncio
    async def test_transform_applies_transformers(self, transformer: ValueTransformer) -> None:
        """Verify transform applies value transformers."""
        result = await transformer.transform({"name": "hello", "price": 5, "keep": "same"})
        assert result["name"] == "HELLO"
        assert result["price"] == 10
        assert result["keep"] == "same"

    @pytest.mark.asyncio
    async def test_transform_missing_field_skipped(self, transformer: ValueTransformer) -> None:
        """Verify missing field is skipped."""
        result = await transformer.transform({"other": "value"})
        assert result == {"other": "value"}

    @pytest.mark.asyncio
    async def test_transform_exception_raises(self, transformer: ValueTransformer) -> None:
        """Verify transformer exception raises TransformationError."""
        vt = ValueTransformer(transformers={"field": lambda v: v.nonexistent})
        with pytest.raises(TransformationError, match="Value transformation for field 'field' failed"):
            await vt.transform({"field": "value"})


class TestTransformationFunctions:
    """Tests for standalone transformation functions."""

    def test_lowercase_text(self) -> None:
        """Verify lowercase_text lowercases strings."""
        assert lowercase_text("HELLO") == "hello"
        assert lowercase_text("Hello World") == "hello world"

    def test_lowercase_text_non_string(self) -> None:
        """Verify lowercase_text returns non-strings unchanged."""
        assert lowercase_text(123) == 123
        assert lowercase_text(None) is None

    def test_trim_text(self) -> None:
        """Verify trim_text strips whitespace."""
        assert trim_text("  hello  ") == "hello"
        assert trim_text("hello") == "hello"

    def test_trim_text_non_string(self) -> None:
        """Verify trim_text returns non-strings unchanged."""
        assert trim_text(123) == 123

    def test_normalize_whitespace(self) -> None:
        """Verify normalize_whitespace collapses whitespace."""
        assert normalize_whitespace("hello   world") == "hello world"
        assert normalize_whitespace("  hello world  ") == "hello world"

    def test_normalize_whitespace_non_string(self) -> None:
        """Verify normalize_whitespace returns non-strings unchanged."""
        assert normalize_whitespace(123) == 123

    def test_extract_keywords(self) -> None:
        """Verify extract_keywords returns keywords meeting min length."""
        result = extract_keywords("the cat sat on the mat", min_length=3)
        assert "cat" in result
        assert "sat" in result
        assert "mat" in result
        assert "on" not in result

    def test_extract_keywords_non_string(self) -> None:
        """Verify extract_keywords returns empty list for non-strings."""
        assert extract_keywords(123) == []
        assert extract_keywords(None) == []

    def test_format_date_datetime(self) -> None:
        """Verify format_date formats datetime objects."""
        d = datetime(2024, 1, 15, 10, 30, 0)
        assert format_date(d) == "2024-01-15"

    def test_format_date_iso_string(self) -> None:
        """Verify format_date parses ISO string."""
        assert format_date("2024-01-15T10:30:00") == "2024-01-15"

    def test_format_date_invalid_string(self) -> None:
        """Verify format_date returns original string if unparseable."""
        assert format_date("not-a-date") == "not-a-date"

    def test_format_date_non_datetime(self) -> None:
        """Verify format_date converts non-datetime to string."""
        assert format_date(42) == "42"

    def test_format_date_custom_format(self) -> None:
        """Verify format_date uses custom format string."""
        d = datetime(2024, 1, 15, 10, 30, 0)
        assert format_date(d, "%d/%m/%Y") == "15/01/2024"

    def test_join_list_strings(self) -> None:
        """Verify join_list joins list items."""
        assert join_list(["a", "b", "c"]) == "a b c"

    def test_join_list_custom_separator(self) -> None:
        """Verify join_list uses custom separator."""
        assert join_list(["a", "b", "c"], ",") == "a,b,c"

    def test_join_list_non_list(self) -> None:
        """Verify join_list converts non-list to string."""
        assert join_list("hello") == "hello"

    def test_split_text_string(self) -> None:
        """Verify split_text splits by default separator."""
        assert split_text("a,b,c") == ["a", "b", "c"]

    def test_split_text_custom_separator(self) -> None:
        """Verify split_text uses custom separator."""
        assert split_text("a|b|c", "|") == ["a", "b", "c"]

    def test_split_text_non_string(self) -> None:
        """Verify split_text wraps non-string in list."""
        assert split_text(123) == ["123"]

    def test_numeric_range_clamps_min(self) -> None:
        """Verify numeric_range clamps to min value."""
        assert numeric_range(5, min_val=10) == 10

    def test_numeric_range_clamps_max(self) -> None:
        """Verify numeric_range clamps to max value."""
        assert numeric_range(15, max_val=10) == 10

    def test_numeric_range_both_bounds(self) -> None:
        """Verify numeric_range clamps to both bounds."""
        assert numeric_range(5, min_val=10, max_val=20) == 10
        assert numeric_range(25, min_val=10, max_val=20) == 20
        assert numeric_range(15, min_val=10, max_val=20) == 15

    def test_numeric_range_non_numeric(self) -> None:
        """Verify numeric_range returns non-numeric unchanged."""
        assert numeric_range("hello") == "hello"

    def test_numeric_range_float(self) -> None:
        """Verify numeric_range works with floats."""
        assert numeric_range(3.14, min_val=0.0, max_val=3.0) == 3.0

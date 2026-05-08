"""Document Transformation for Indexing"""

from __future__ import annotations

from abc import abstractmethod
from dataclasses import dataclass
from dataclasses import field as dataclass_field
from datetime import datetime
from typing import TYPE_CHECKING, Any, cast

from lexigram.primitives.data import ReadOnlyMapper
from lexigram.search.exceptions import TransformationError

if TYPE_CHECKING:
    from collections.abc import Callable


@dataclass
class TransformationRule:
    """Document transformation rule"""

    field: str
    transform_func: Callable[[Any], Any]
    condition: Callable[[dict[str, Any]], bool] | None = None
    required: bool = False


@dataclass
class TransformationPipeline:
    """Pipeline of transformation rules"""

    name: str
    rules: list[TransformationRule] = dataclass_field(default_factory=list)
    pre_transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None
    post_transform: Callable[[dict[str, Any]], dict[str, Any]] | None = None


class DocumentTransformer(ReadOnlyMapper[dict[str, Any], dict[str, Any]]):
    """Base class for document transformers.

    Extends ``ReadOnlyMapper[dict, dict]`` from ``lexigram.data.mapper`` so
    that all search document transformers conform to the standard data-layer
    mapper contract.  The ``to_target`` / ``to_target_batch`` methods map
    directly onto the former ``transform`` / ``transform_batch`` interface.
    """

    @abstractmethod
    async def to_target(self, source: dict[str, Any]) -> dict[str, Any]:
        """Transform a source document into its indexed representation."""

    async def to_target_batch(
        self,
        sources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Transform multiple documents; default maps sequentially."""
        return [await self.to_target(doc) for doc in sources]


class DefaultDocumentTransformer(DocumentTransformer):
    """Default document transformer with pipeline support."""

    def __init__(self, pipelines: list[TransformationPipeline] | None = None):
        self.pipelines = pipelines or []

    def add_pipeline(self, pipeline: TransformationPipeline) -> None:
        """Add a transformation pipeline."""
        self.pipelines.append(pipeline)

    async def to_target(self, source: dict[str, Any]) -> dict[str, Any]:
        """Transform a single document through all registered pipelines."""
        transformed = source.copy()

        for pipeline in self.pipelines:
            try:
                transformed = await self._apply_pipeline(transformed, pipeline)
            except Exception as e:
                raise TransformationError(
                    f"Pipeline '{pipeline.name}' failed: {e}",
                ) from e

        return transformed

    async def to_target_batch(
        self,
        sources: list[dict[str, Any]],
    ) -> list[dict[str, Any]]:
        """Transform multiple documents concurrently."""
        import asyncio

        tasks = [self.to_target(doc) for doc in sources]
        return await asyncio.gather(*tasks)

    async def _apply_pipeline(
        self,
        document: dict[str, Any],
        pipeline: TransformationPipeline,
    ) -> dict[str, Any]:
        """Apply a transformation pipeline to a document."""
        if pipeline.pre_transform:
            document = pipeline.pre_transform(document)

        for rule in pipeline.rules:
            if rule.condition and not rule.condition(document):
                continue

            try:
                value = document.get(rule.field)
                if value is not None or rule.required:
                    transformed_value = rule.transform_func(value)
                    document[rule.field] = transformed_value
            except Exception as e:
                if rule.required:
                    raise TransformationError(
                        f"Required transformation for field '{rule.field}' failed: {e}",
                    ) from e

        if pipeline.post_transform:
            document = pipeline.post_transform(document)

        return document


class FieldMapper:
    """Maps and transforms document fields"""

    def __init__(self, mappings: dict[str, str] | None = None):
        self.mappings = mappings or {}

    def add_mapping(self, from_field: str, to_field: str) -> None:
        """Add a field mapping"""
        self.mappings[from_field] = to_field

    async def transform(self, document: dict[str, Any]) -> dict[str, Any]:
        """Apply field mappings"""
        transformed = {}

        for key, value in document.items():
            new_key = self.mappings.get(key, key)
            transformed[new_key] = value

        return transformed


class ValueTransformer:
    """Transforms field values"""

    def __init__(self, transformers: dict[str, Callable] | None = None):
        self.transformers = transformers or {}

    def add_transformer(self, field: str, transformer: Callable) -> None:
        """Add a field transformer"""
        self.transformers[field] = transformer

    async def transform(self, document: dict[str, Any]) -> dict[str, Any]:
        """Apply value transformations"""
        transformed = document.copy()

        for field, transformer in self.transformers.items():
            if field in transformed:
                try:
                    transformed[field] = transformer(transformed[field])
                except Exception as e:
                    raise TransformationError(
                        f"Value transformation for field '{field}' failed: {e}",
                    ) from e

        return transformed


# Common transformation functions
def lowercase_text(value: Any) -> str:
    """Convert text to lowercase"""
    if isinstance(value, str):
        return value.lower()
    return cast("str", value)


def trim_text(value: Any) -> str:
    """Trim whitespace from text"""
    if isinstance(value, str):
        return value.strip()
    return cast("str", value)


def normalize_whitespace(value: Any) -> str:
    """Normalize whitespace in text"""
    if isinstance(value, str):
        import re

        return re.sub(r"\s+", " ", value.strip())
    return cast("str", value)


def extract_keywords(value: Any, min_length: int = 3) -> list[str]:
    """Extract keywords from text"""
    if isinstance(value, str):
        import re

        words = re.findall(r"\b\w+\b", value.lower())
        return list(filter(lambda word: len(word) >= min_length, words))
    return []


def format_date(value: Any, format_str: str = "%Y-%m-%d") -> str:
    """Format date value"""
    if isinstance(value, datetime):
        return value.strftime(format_str)
    if isinstance(value, str):
        # Try to parse and reformat
        try:
            parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
            return parsed.strftime(format_str)
        except (ValueError, TypeError):
            return value
    return str(value)


def join_list(value: Any, separator: str = " ") -> str:
    """Join list items into string"""
    if isinstance(value, list):
        return separator.join(str(item) for item in value)
    return str(value)


def split_text(value: Any, separator: str = ",") -> list[str]:
    """Split text into list"""
    if isinstance(value, str):
        return list(filter(None, map(str.strip, value.split(separator))))
    return [str(value)]


def numeric_range(
    value: float,
    min_val: float | None = None,
    max_val: float | None = None,
) -> int | float:
    """Constrain numeric value to range"""
    if isinstance(value, (int, float)):
        if min_val is not None:
            value = max(value, min_val)
        if max_val is not None:
            value = min(value, max_val)
    return value


__all__ = [
    "DefaultDocumentTransformer",
    "DocumentTransformer",
    "FieldMapper",
    "TransformationPipeline",
    "TransformationRule",
    "ValueTransformer",
    "extract_keywords",
    "format_date",
    "join_list",
    "lowercase_text",
    "normalize_whitespace",
    "numeric_range",
    "split_text",
    "trim_text",
]

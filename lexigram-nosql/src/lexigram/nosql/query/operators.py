"""MongoDB operator constants and registry.

Provides a centralized registry of MongoDB query and update operators
so that query builder components can reference operators by symbolic
name rather than raw string literals.
"""

from __future__ import annotations

from enum import StrEnum


class ComparisonOp(StrEnum):
    """MongoDB comparison operators."""

    EQ = "$eq"
    NE = "$ne"
    GT = "$gt"
    GTE = "$gte"
    LT = "$lt"
    LTE = "$lte"
    IN = "$in"
    NIN = "$nin"


class LogicalOp(StrEnum):
    """MongoDB logical operators."""

    AND = "$and"
    OR = "$or"
    NOT = "$not"
    NOR = "$nor"


class ElementOp(StrEnum):
    """MongoDB element operators."""

    EXISTS = "$exists"
    TYPE = "$type"


class EvaluationOp(StrEnum):
    """MongoDB evaluation operators."""

    REGEX = "$regex"
    TEXT = "$text"
    EXPR = "$expr"
    MOD = "$mod"
    WHERE = "$where"


class ArrayOp(StrEnum):
    """MongoDB array operators."""

    ALL = "$all"
    ELEM_MATCH = "$elemMatch"
    SIZE = "$size"


class UpdateOp(StrEnum):
    """MongoDB update operators."""

    SET = "$set"
    UNSET = "$unset"
    INC = "$inc"
    MUL = "$mul"
    RENAME = "$rename"
    MIN = "$min"
    MAX = "$max"
    CURRENT_DATE = "$currentDate"
    PUSH = "$push"
    PULL = "$pull"
    ADD_TO_SET = "$addToSet"
    POP = "$pop"


class AggregationOp(StrEnum):
    """MongoDB aggregation stage operators."""

    MATCH = "$match"
    GROUP = "$group"
    PROJECT = "$project"
    SORT = "$sort"
    LIMIT = "$limit"
    SKIP = "$skip"
    UNWIND = "$unwind"
    LOOKUP = "$lookup"
    ADD_FIELDS = "$addFields"
    FACET = "$facet"
    COUNT = "$count"
    BUCKET = "$bucket"
    BUCKET_AUTO = "$bucketAuto"
    REPLACE_ROOT = "$replaceRoot"
    MERGE = "$merge"
    OUT = "$out"


class AccumulatorOp(StrEnum):
    """MongoDB aggregation accumulator operators."""

    SUM = "$sum"
    AVG = "$avg"
    FIRST = "$first"
    LAST = "$last"
    MAX = "$max"
    MIN = "$min"
    PUSH = "$push"
    ADD_TO_SET = "$addToSet"
    STD_DEV_POP = "$stdDevPop"
    STD_DEV_SAMP = "$stdDevSamp"


__all__ = [
    "AccumulatorOp",
    "AggregationOp",
    "ArrayOp",
    "ComparisonOp",
    "ElementOp",
    "EvaluationOp",
    "LogicalOp",
    "UpdateOp",
]

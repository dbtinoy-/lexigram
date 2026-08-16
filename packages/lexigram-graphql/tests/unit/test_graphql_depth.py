"""Unit tests for GraphQL depth limiting."""

import pytest
from unittest.mock import MagicMock
from graphql import parse

from lexigram.graphql.security.depth import (
    DepthLimitValidator,
    DepthLimitExtension,
    create_depth_limit
)
from lexigram.graphql.exceptions import QueryTooDeepError

class TestDepthLimitValidator:
    """Test DepthLimitValidator functionality."""

    def test_get_depth(self):
        """Test calculating depth."""
        query = "{ a { b { c } } }"
        document = parse(query)
        validator = DepthLimitValidator()
        
        assert validator.get_depth(document) == 2 # a->b->c is depth 2? "a" is 0, "b" is 1, "c" is 2?
        # Let's re-verify the logic in source code:
        # _calculate_depth(selection_set, 0)
        #   loops a:
        #     _calculate_depth(a.selection_set, 1)
        #       loops b:
        #         _calculate_depth(b.selection_set, 2)
        #           loops c:
        #             no selection set.
        #           returns 2
        #       returns 2
        # max_depth = 2.
        # Corret.

    def test_validate_ok(self):
        """Test validation passes."""
        query = "{ a { b } }" # Depth 1
        document = parse(query)
        validator = DepthLimitValidator(max_depth=2)
        
        validator.validate(document)

    def test_validate_fail(self):
        query = "{ a { b { c } } }"  # depth 2
        document = parse(query)
        validator = DepthLimitValidator(max_depth=1)

        with pytest.raises(QueryTooDeepError):
            validator.validate(document)

    def test_ignore_introspection(self):
        """Test ignoring introspection queries."""
        query = "{ __schema { types { name } } }"
        document = parse(query)
        validator = DepthLimitValidator(max_depth=1, ignore_introspection=True)
        
        # Should pass because introspection is ignored
        validator.validate(document)
        assert validator.get_depth(document) == 0

    def test_fragment_spread_contributes_to_depth(self) -> None:
        """FragmentSpread must not be silently skipped — it should count as depth."""
        query = """
            fragment Deep on SomeType { b { c } }
            { a { ...Deep } }
        """
        document = parse(query)
        validator = DepthLimitValidator(max_depth=10)

        # a → (fragment spread) → b → c gives depth 2 (same as { a { b { c } } })
        assert validator.get_depth(document) == 2

    def test_fragment_spread_triggers_limit(self) -> None:
        """A query that hides depth inside a fragment must still be rejected."""
        query = """
            fragment TooDeep on SomeType { b { c { d } } }
            { a { ...TooDeep } }
        """
        document = parse(query)
        # a -> b -> c -> d  = depth 3; limit is 2
        validator = DepthLimitValidator(max_depth=2)

        with pytest.raises(QueryTooDeepError):
            validator.validate(document)

    def test_inline_fragment_transparent(self) -> None:
        """InlineFragment is transparent — it must not add an extra depth level."""
        # { a { ... on T { b { c } } } } has the same depth as { a { b { c } } } = 2
        query_inline = "{ a { ... on SomeType { b { c } } } }"
        query_plain = "{ a { b { c } } }"

        document_inline = parse(query_inline)
        document_plain = parse(query_plain)
        validator = DepthLimitValidator()

        assert validator.get_depth(document_inline) == validator.get_depth(document_plain)

    def test_cyclic_fragment_does_not_infinite_loop(self) -> None:
        """Cyclically-defined fragments must not cause infinite recursion."""
        # graphql-core rejects recursive fragments at parse/validation time, but
        # the validator itself must be safe regardless.
        query = """
            fragment A on T { ...B }
            fragment B on T { ...A }
            { root { ...A } }
        """
        document = parse(query)
        validator = DepthLimitValidator(max_depth=100)
        # Should complete without hitting Python recursion limit
        depth = validator.get_depth(document)
        assert depth >= 0


class TestDepthLimitExtension:
    """Test strawberry extension."""

    def test_on_validate(self):
        """The extension validates the document during the validation hook."""

        def make_ext(max_depth):
            ext = create_depth_limit(max_depth=max_depth)
            ext.execution_context = MagicMock(graphql_document=parse("{ a { b } }"))
            return ext

        # Pass case: depth 1 <= limit 2
        gen = make_ext(max_depth=2).on_validate()
        next(gen)
        with pytest.raises(StopIteration):
            next(gen)

        # Fail case: depth 1 > limit 0
        ext = create_depth_limit(max_depth=0)
        ext.execution_context = MagicMock(graphql_document=parse("{ a { b } }"))
        gen = ext.on_validate()

        with pytest.raises(QueryTooDeepError):
            next(gen)

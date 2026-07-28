"""Tests for M30/M31/N18: SearchQueryBuilder fuzzy, autocomplete, geo_distance, date_histogram_agg."""

import pytest

from lexigram.search.query.builder import SearchQueryBuilder
from lexigram.search.query.types import AutocompleteQuery, FuzzyQuery, GeoDistanceFilter


class TestSearchQueryBuilderNewMethods:
    """M30/M31/N18: New SearchQueryBuilder query methods."""

    @pytest.fixture
    def builder(self) -> SearchQueryBuilder:
        return SearchQueryBuilder()

    # ── fuzzy() ──────────────────────────────────────────────────────────────

    def test_fuzzy_adds_fuzzy_query_to_result(self, builder: SearchQueryBuilder) -> None:
        """fuzzy() produces a fuzzy_queries entry in the built SearchQuery."""
        q = builder.fuzzy("title", "serach", fuzziness=2).build()
        assert q.fuzzy_queries is not None
        assert len(q.fuzzy_queries) == 1
        assert q.fuzzy_queries[0] == {"field": "title", "value": "serach", "fuzziness": 2}

    def test_fuzzy_default_fuzziness_is_auto(self, builder: SearchQueryBuilder) -> None:
        """fuzzy() defaults fuzziness to 'auto'."""
        q = builder.fuzzy("name", "jon").build()
        assert q.fuzzy_queries[0]["fuzziness"] == "auto"

    def test_multiple_fuzzy_queries(self, builder: SearchQueryBuilder) -> None:
        """Multiple fuzzy() calls accumulate distinct entries."""
        q = builder.fuzzy("title", "helo").fuzzy("body", "wrold").build()
        assert len(q.fuzzy_queries) == 2

    def test_no_fuzzy_returns_none(self, builder: SearchQueryBuilder) -> None:
        """fuzzy_queries is None when no fuzzy() calls made."""
        q = builder.query("something").build()
        assert q.fuzzy_queries is None

    def test_fuzzy_returns_builder_for_chaining(self, builder: SearchQueryBuilder) -> None:
        """fuzzy() returns self for fluent chaining."""
        result = builder.fuzzy("f", "v")
        assert result is builder

    # ── autocomplete() ───────────────────────────────────────────────────────

    def test_autocomplete_adds_entry(self, builder: SearchQueryBuilder) -> None:
        """autocomplete() produces an autocomplete_queries entry."""
        q = builder.autocomplete("title", "hel").build()
        assert q.autocomplete_queries is not None
        assert q.autocomplete_queries[0] == {"field": "title", "prefix": "hel"}

    def test_no_autocomplete_returns_none(self, builder: SearchQueryBuilder) -> None:
        """autocomplete_queries is None when no autocomplete() calls made."""
        q = builder.build()
        assert q.autocomplete_queries is None

    def test_autocomplete_returns_builder_for_chaining(self, builder: SearchQueryBuilder) -> None:
        """autocomplete() returns self for fluent chaining."""
        result = builder.autocomplete("title", "te")
        assert result is builder

    # ── geo_distance() ───────────────────────────────────────────────────────

    def test_geo_distance_adds_filter(self, builder: SearchQueryBuilder) -> None:
        """geo_distance() produces a geo_filters entry with correct fields."""
        q = builder.geo_distance("location", 48.8566, 2.3522, "10km").build()
        assert q.geo_filters is not None
        gf = q.geo_filters[0]
        assert gf["field"] == "location"
        assert gf["lat"] == 48.8566
        assert gf["lon"] == 2.3522
        assert gf["distance"] == "10km"

    def test_no_geo_returns_none(self, builder: SearchQueryBuilder) -> None:
        """geo_filters is None when no geo_distance() calls made."""
        q = builder.build()
        assert q.geo_filters is None

    def test_geo_distance_returns_builder_for_chaining(self, builder: SearchQueryBuilder) -> None:
        """geo_distance() returns self for fluent chaining."""
        result = builder.geo_distance("loc", 0.0, 0.0, "1km")
        assert result is builder

    # ── date_histogram_agg() ─────────────────────────────────────────────────

    def test_date_histogram_agg_creates_aggregation(self, builder: SearchQueryBuilder) -> None:
        """date_histogram_agg() creates a date_histogram aggregation entry."""
        q = builder.date_histogram_agg("by_day", "created_at", "1d").build()
        assert q.aggregations is not None
        agg = q.aggregations["by_day"]
        assert agg["type"] == "date_histogram"
        assert agg["field"] == "created_at"
        assert agg["interval"] == "1d"

    def test_date_histogram_agg_default_interval(self, builder: SearchQueryBuilder) -> None:
        """date_histogram_agg() uses '1d' as default interval."""
        q = builder.date_histogram_agg("by_day", "ts").build()
        assert q.aggregations["by_day"]["interval"] == "1d"

    def test_date_histogram_agg_returns_builder_for_chaining(self, builder: SearchQueryBuilder) -> None:
        """date_histogram_agg() returns self for fluent chaining."""
        result = builder.date_histogram_agg("h", "f")
        assert result is builder

    # ── reset() clears new state ──────────────────────────────────────────────

    def test_reset_clears_fuzzy_autocomplete_geo(self, builder: SearchQueryBuilder) -> None:
        """reset() clears fuzzy, autocomplete, and geo state."""
        builder.fuzzy("f", "v").autocomplete("f", "p").geo_distance("loc", 0.0, 0.0, "1km")
        builder.reset()
        q = builder.build()
        assert q.fuzzy_queries is None
        assert q.autocomplete_queries is None
        assert q.geo_filters is None

    # ── clone() copies new state ──────────────────────────────────────────────

    def test_clone_copies_fuzzy_autocomplete_geo(self, builder: SearchQueryBuilder) -> None:
        """clone() copies fuzzy, autocomplete, and geo state."""
        builder.fuzzy("title", "test").autocomplete("name", "te").geo_distance("loc", 1.0, 2.0, "5km")
        clone = builder.clone()

        q_orig = builder.build()
        q_clone = clone.build()

        assert q_orig.fuzzy_queries == q_clone.fuzzy_queries
        assert q_orig.autocomplete_queries == q_clone.autocomplete_queries
        assert q_orig.geo_filters == q_clone.geo_filters

    def test_clone_is_independent(self, builder: SearchQueryBuilder) -> None:
        """Mutating the clone does not affect the original."""
        builder.fuzzy("f", "v")
        clone = builder.clone()
        clone.fuzzy("other", "x")

        assert len(builder._fuzzy_queries) == 1
        assert len(clone._fuzzy_queries) == 2

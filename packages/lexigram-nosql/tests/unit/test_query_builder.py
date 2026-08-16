"""Tests for DocumentQueryBuilder."""

from __future__ import annotations

from lexigram.nosql.query.builder import DocumentQuery, DocumentQueryBuilder


class TestDocumentQueryBuilder:
    """Tests for the fluent query builder."""

    def test_empty_build(self) -> None:
        query = DocumentQueryBuilder().build()
        assert query.filter == {}
        assert query.projection is None
        assert query.sort is None
        assert query.skip == 0
        assert query.limit == 0

    def test_where_exact(self) -> None:
        query = DocumentQueryBuilder().where("status", "active").build()
        assert query.filter == {"status": "active"}

    def test_where_ne(self) -> None:
        query = DocumentQueryBuilder().where_ne("status", "deleted").build()
        assert query.filter == {"status": {"$ne": "deleted"}}

    def test_where_gt(self) -> None:
        query = DocumentQueryBuilder().where_gt("age", 18).build()
        assert query.filter == {"age": {"$gt": 18}}

    def test_where_gte(self) -> None:
        query = DocumentQueryBuilder().where_gte("count", 5).build()
        assert query.filter == {"count": {"$gte": 5}}

    def test_where_lt(self) -> None:
        query = DocumentQueryBuilder().where_lt("price", 100).build()
        assert query.filter == {"price": {"$lt": 100}}

    def test_where_lte(self) -> None:
        query = DocumentQueryBuilder().where_lte("stock", 0).build()
        assert query.filter == {"stock": {"$lte": 0}}

    def test_where_between(self) -> None:
        query = DocumentQueryBuilder().where_between("age", 18, 65).build()
        assert query.filter == {"age": {"$gte": 18, "$lte": 65}}

    def test_where_in(self) -> None:
        query = DocumentQueryBuilder().where_in("role", ["admin", "mod"]).build()
        assert query.filter == {"role": {"$in": ["admin", "mod"]}}

    def test_where_not_in(self) -> None:
        query = DocumentQueryBuilder().where_not_in("status", ["banned"]).build()
        assert query.filter == {"status": {"$nin": ["banned"]}}

    def test_where_exists(self) -> None:
        query = DocumentQueryBuilder().where_exists("email").build()
        assert query.filter == {"email": {"$exists": True}}

    def test_where_exists_false(self) -> None:
        query = DocumentQueryBuilder().where_exists("phone", False).build()
        assert query.filter == {"phone": {"$exists": False}}

    def test_where_type(self) -> None:
        query = DocumentQueryBuilder().where_type("age", "int").build()
        assert query.filter == {"age": {"$type": "int"}}

    def test_where_regex(self) -> None:
        query = DocumentQueryBuilder().where_regex("name", "^J", "i").build()
        assert query.filter == {"name": {"$regex": "^J", "$options": "i"}}

    def test_where_text(self) -> None:
        query = DocumentQueryBuilder().where_text("hello world").build()
        assert query.filter == {"$text": {"$search": "hello world"}}

    def test_and_where(self) -> None:
        query = DocumentQueryBuilder().and_where(
            {"status": "active"}, {"age": {"$gt": 18}},
        ).build()
        assert query.filter == {
            "$and": [{"status": "active"}, {"age": {"$gt": 18}}],
        }

    def test_or_where(self) -> None:
        query = DocumentQueryBuilder().or_where(
            {"role": "admin"}, {"role": "moderator"},
        ).build()
        assert query.filter == {
            "$or": [{"role": "admin"}, {"role": "moderator"}],
        }

    def test_select_projection(self) -> None:
        query = DocumentQueryBuilder().select("name", "email").build()
        assert query.projection == {"name": 1, "email": 1}

    def test_exclude_projection(self) -> None:
        query = DocumentQueryBuilder().exclude("password").build()
        assert query.projection == {"password": 0}

    def test_sort_ascending(self) -> None:
        query = DocumentQueryBuilder().sort_by("created_at").build()
        assert query.sort == [("created_at", 1)]

    def test_sort_descending(self) -> None:
        query = DocumentQueryBuilder().sort_by("created_at", descending=True).build()
        assert query.sort == [("created_at", -1)]

    def test_multi_sort(self) -> None:
        query = (
            DocumentQueryBuilder()
            .sort_by("priority", descending=True)
            .sort_by("name")
            .build()
        )
        assert query.sort == [("priority", -1), ("name", 1)]

    def test_skip_limit(self) -> None:
        query = DocumentQueryBuilder().skip(20).limit(10).build()
        assert query.skip == 20
        assert query.limit == 10

    def test_chained_complex_query(self) -> None:
        query = (
            DocumentQueryBuilder()
            .where("status", "active")
            .where_gt("age", 18)
            .where_in("role", ["admin", "moderator"])
            .sort_by("created_at", descending=True)
            .skip(20)
            .limit(10)
            .select("name", "email", "role")
            .build()
        )
        assert query.filter["status"] == "active"
        assert query.filter["age"] == {"$gt": 18}
        assert query.filter["role"] == {"$in": ["admin", "moderator"]}
        assert query.sort == [("created_at", -1)]
        assert query.skip == 20
        assert query.limit == 10
        assert query.projection == {"name": 1, "email": 1, "role": 1}

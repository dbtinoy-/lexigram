"""The protected resource — an in-memory article store.

This file teaches two ideas at once:

1. **Stores are plain objects.**  No base class, no framework import — a
   dataclass with methods is enough.  The DI container treats it like any
   other service (see ``di/provider.py``, which registers it as a
   singleton), and swapping this in-memory implementation for Postgres
   later changes nothing outside ``di/``.

2. **The RBAC demo needs something to guard.**  Articles are the resource
   every persona tries to read/create/delete; the permission matrix in
   ``controllers/api.py`` is exercised entirely against this store.

Deliberately *not* here: authorization checks.  Stores stay dumb —
controllers ask ``AuthorizationService`` before touching them.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Article:
    """One demo article row.

    Attributes:
        id: Stable identifier (``a-1``, ``a-2``, … assigned by the store).
        title: Display title.
        body: Body text.
    """

    id: str
    title: str
    body: str


@dataclass
class ArticleStore:
    """In-memory article fixtures owned by the provider.

    Registered as a singleton, so every controller and the seed service
    share one dictionary for the lifetime of the process.
    """

    _articles: dict[str, Article] = field(default_factory=dict)
    _next: int = 1

    def list(self) -> list[Article]:
        """All articles, insertion order."""
        return list(self._articles.values())

    def get(self, article_id: str) -> Article | None:
        """Fetch by id; ``None`` when absent (controller maps to 404)."""
        return self._articles.get(article_id)

    def create(self, title: str, body: str) -> Article:
        """Append a new article with an auto-assigned id."""
        article = Article(id=f"a-{self._next}", title=title, body=body)
        self._next += 1
        self._articles[article.id] = article
        return article

    def delete(self, article_id: str) -> bool:
        """Remove by id; ``True`` when something was actually deleted."""
        return self._articles.pop(article_id, None) is not None


__all__ = ["Article", "ArticleStore"]

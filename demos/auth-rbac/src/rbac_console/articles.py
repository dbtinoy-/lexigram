"""Articles fixture store — the protected resource the RBAC demo guards."""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Article:
    """One demo article row.

    Attributes:
        id: Stable identifier.
        title: Display title.
        body: Body text.
    """

    id: str
    title: str
    body: str


@dataclass
class ArticleStore:
    """In-memory article fixtures owned by the provider."""

    _articles: dict[str, Article] = field(default_factory=dict)
    _next: int = 1

    def list(self) -> list[Article]:
        return list(self._articles.values())

    def get(self, article_id: str) -> Article | None:
        return self._articles.get(article_id)

    def create(self, title: str, body: str) -> Article:
        article = Article(id=f"a-{self._next}", title=title, body=body)
        self._next += 1
        self._articles[article.id] = article
        return article

    def delete(self, article_id: str) -> bool:
        return self._articles.pop(article_id, None) is not None


__all__ = ["Article", "ArticleStore"]

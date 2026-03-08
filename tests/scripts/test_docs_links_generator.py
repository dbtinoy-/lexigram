"""Tests for the docs-links audit generator."""

from __future__ import annotations

from pathlib import Path


def _write_workspace(root: Path) -> None:
    """Create a docs corpus with mixed good/bad internal links."""

    docs = root / "docs" / "lexigram-docs"
    (docs / "fundamentals").mkdir(parents=True)
    (docs / "guides").mkdir()
    (docs / "ecosystem").mkdir()

    (docs / "fundamentals" / "providers.md").write_text(
        "## Provider Priorities\n\nSee the guides.\n", encoding="utf-8"
    )
    (docs / "guides" / "real-time.md").write_text(
        "- [Providers](/fundamentals/providers/)\n"
        "- [Anchored](/fundamentals/providers/#provider-priorities)\n"
        "- [Missing target](/fundamentals/routing/)\n"
        "- [Bad anchor](/fundamentals/providers/#nope)\n",
        encoding="utf-8",
    )
    (docs / "ecosystem" / "index.md").write_text(
        "- [Web package](/packages/lexigram-web/)\n", encoding="utf-8"
    )

    # A documented package (owner of docs/) and one without docs/.
    (root / "lexigram-web" / "docs").mkdir(parents=True)
    (root / "lexigram-web" / "docs" / "index.md").write_text("# web\n", encoding="utf-8")
    (root / "lexigram-bare").mkdir()


def test_docs_links_generator_reports_dead_links(tmp_path: Path) -> None:
    from scripts.audit.generators.docs_links import DocsLinksAuditGenerator

    _write_workspace(tmp_path)

    generator = DocsLinksAuditGenerator()
    result = generator.run(root=tmp_path, all_mode=True)
    markdown = (tmp_path / "AUDIT_DOC_LINKS.md").read_text(encoding="utf-8")

    assert result.success is False
    assert "2 dead link(s)" in result.message
    assert "## Dead Links" in markdown
    assert "`/fundamentals/routing/`" in markdown
    assert "anchor `#nope` not found" in markdown
    # The good (resolvable) anchor link is never flagged.
    assert "anchor `#provider-priorities`" not in markdown


def test_docs_links_generator_package_route_checks_docs_folder(tmp_path: Path) -> None:
    from scripts.audit.generators.docs_links import DocsLinksAuditGenerator

    _write_workspace(tmp_path)
    (tmp_path / "docs" / "lexigram-docs" / "ecosystem" / "index.md").write_text(
        "- [Bare package](/packages/lexigram-bare/)\n", encoding="utf-8"
    )

    generator = DocsLinksAuditGenerator()
    result = generator.run(root=tmp_path, all_mode=True)
    markdown = (tmp_path / "AUDIT_DOC_LINKS.md").read_text(encoding="utf-8")

    assert result.success is False
    assert "`/packages/lexigram-bare/`" in markdown


def test_docs_links_generator_clean_corpus(tmp_path: Path) -> None:
    from scripts.audit.generators.docs_links import DocsLinksAuditGenerator

    _write_workspace(tmp_path)
    # Fix the remaining dead targets so the corpus is fully clean.
    (tmp_path / "docs" / "lexigram-docs" / "guides" / "web.md").write_text(
        "# Web\n", encoding="utf-8"
    )
    (tmp_path / "docs" / "lexigram-docs" / "fundamentals" / "routing.md").write_text(
        "# Routing\n", encoding="utf-8"
    )
    (tmp_path / "docs" / "lexigram-docs" / "fundamentals" / "providers.md").write_text(
        "## Provider Priorities\n\n## Sub Section\n\n"
        "## Nope\n",  # add the missing anchor
        encoding="utf-8",
    )

    generator = DocsLinksAuditGenerator()
    result = generator.run(root=tmp_path, all_mode=True)
    markdown = (tmp_path / "AUDIT_DOC_LINKS.md").read_text(encoding="utf-8")

    assert result.success is True
    assert "Dead links: 0" in markdown
    assert "No dead internal links detected." in markdown
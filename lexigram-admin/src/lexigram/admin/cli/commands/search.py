from __future__ import annotations

import asyncio
import importlib
from pathlib import Path
from typing import Annotated, Any

import typer


def create_app():
    """Create the search CLI command group (Typer app).

    Called by ``lexigram-cli``'s command loader.
    """

    app = typer.Typer(name="search", help="Search index management")

    @app.command()
    def reindex(
        config_path: Annotated[
            Path,
            typer.Argument(
                help="Path to application.yaml (default: ./application.yaml)",
            ),
        ] = Path("application.yaml"),
        app_module: Annotated[
            str | None,
            typer.Option(
                "--app-module",
                "-m",
                help="Module path to root module, e.g. 'mypackage.root:RootModule'",
            ),
        ] = None,
    ) -> None:
        """Reindex all searchable resources.

        Boots the application from *config_path*, discovers all admin resources
        with a ``searchable`` spec, queries every record from each resource's
        data source, and indexes them through the configured search engine.
        """
        asyncio.run(_run_reindex(config_path=config_path, app_module=app_module))

    return app


async def _run_reindex(config_path: Path, app_module: str | None) -> None:
    from typer import Exit as TyperExit
    from typer import echo

    from lexigram.app import Application
    from lexigram.config.loader import ConfigLoader  # type: ignore[import-untyped]
    from lexigram.config.main import LexigramConfig

    if app_module is None:
        echo("Error: --app-module is required", err=True)
        raise TyperExit(1)

    config = ConfigLoader().load_sync(LexigramConfig, config_path)

    module_path, _, class_name = app_module.rpartition(":")
    try:
        mod = importlib.import_module(module_path)
    except ImportError as exc:
        echo(f"Error: cannot import module '{module_path}': {exc}", err=True)
        raise TyperExit(1) from None
    root_cls = getattr(mod, class_name, None)
    if root_cls is None:
        echo(f"Error: class '{class_name}' not found in '{module_path}'", err=True)
        raise TyperExit(1)

    echo("Booting application...")
    dm = root_cls.configure(config=config)

    try:
        async with Application.boot(modules=[dm], config=config) as app:
            echo("Collecting searchable resources...")
            searchable = await _collect_searchable(app.container)
            if not searchable:
                echo("No searchable resources found.")
                return

            _log_banner(searchable)

            from lexigram.contracts.search import SearchEngineProtocol

            search_engine = await app.container.resolve(
                SearchEngineProtocol,
                bypass_visibility=True,
            )

            total = 0
            for resource_cls, searchable_spec in searchable:
                dsc = getattr(resource_cls, "_data_source_class", None)
                if dsc is None:
                    _log_warn(resource_cls, "no _data_source_class")
                    continue
                try:
                    ds = await app.container.resolve(dsc, bypass_visibility=True)
                except Exception as exc:
                    _log_warn(resource_cls, f"resolve failed: {exc}")
                    continue

                repo = getattr(ds, "_repo", None)
                if repo is None:
                    _log_warn(resource_cls, "no _repo on data source")
                    continue

                echo(f"  Fetching {searchable_spec.index_name}...")
                try:
                    records = await repo.find(limit=None)
                except Exception as exc:
                    _log_warn(resource_cls, f"find failed: {exc}")
                    continue

                if not records:
                    echo("    -> 0 records")
                    continue

                docs = _build_documents(records, searchable_spec)
                try:
                    await search_engine.index(searchable_spec.index_name, docs)
                except Exception as exc:
                    _log_warn(resource_cls, f"index failed: {exc}")
                    continue

                echo(f"    -> indexed {len(docs)} document(s)")
                total += len(docs)

            echo(f"\nReindex complete. {total} document(s) indexed.")
    except Exception as exc:
        echo(f"Error during reindex: {exc}", err=True)
        raise TyperExit(1) from None


async def _collect_searchable(
    container: object,
) -> list[tuple[type, Any]]:
    """Return (resource_class, SearchableSpec) pairs from the admin registry."""
    from lexigram.admin.contributors.registry import ContributorRegistry
    from lexigram.admin.contributors.resource_collector import ResourceCollector
    from lexigram.admin.dashboard.naming_policy import NamingPolicy

    try:
        registry = await container.resolve(  # type: ignore[attr-defined]
            ContributorRegistry,
            bypass_visibility=True,
        )
    except Exception:
        return []

    naming = NamingPolicy(mode="warn")
    collector = ResourceCollector(naming_policy=naming)
    all_contributors = list(registry.get_all())
    resource_classes = collector.collect(all_contributors)

    result: list[tuple[type, object]] = []
    for rc in resource_classes:
        spec = getattr(rc, "searchable", None)
        if spec is not None and getattr(spec, "index_name", None):
            result.append((rc, spec))
    return result


def _build_documents(
    records: list[object],
    searchable: object,
) -> list[dict]:
    """Build search document dicts from *records*.

    The spec is expected to have a ``fields`` iterable.  Each record is
    converted using ``getattr`` (object) or ``get`` (dict) style access.
    """
    fields: tuple[str, ...] = getattr(searchable, "fields", ())
    docs: list[dict] = []
    for record in records:
        if isinstance(record, dict):
            doc_id = record.get("id")
            doc = {f: record.get(f) for f in fields}
        else:
            doc_id = getattr(record, "id", None)
            doc = {f: getattr(record, f, None) for f in fields}
        if doc_id is None:
            continue
        doc["id"] = str(doc_id)
        docs.append(doc)
    return docs


def _log_banner(searchable: list[tuple[type, object]]) -> None:
    from typer import echo

    echo(f"  Found {len(searchable)} searchable resource(s):")
    for rc, spec in searchable:
        echo(f"    - {rc.__name__} -> {getattr(spec, 'index_name', '?')}")


def _log_warn(resource_cls: type, reason: str) -> None:
    from typer import echo

    echo(f"  Skipping {resource_cls.__name__}: {reason}")

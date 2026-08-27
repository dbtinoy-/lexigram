"""Schema baseline diff helper for the GraphQL provider.

Extracted from ``provider.py`` to keep the provider under the 500-LOC
ratchet; behavior is unchanged.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from pathlib import Path

    from lexigram.graphql.config import GraphQLConfig

logger = get_logger(__name__)


def run_schema_diff(config: GraphQLConfig | None, current_schema: Any) -> None:
    """Compare *current_schema* against the configured baseline SDL file.

    Only runs when :attr:`~lexigram.graphql.config.GraphQLConfig.schema_baseline_path`
    is set.  Logs breaking removals at WARNING level and non-breaking additions
    at DEBUG level.

    Args:
        config: The GraphQL configuration (or ``None`` when not configured).
        current_schema: The freshly built Strawberry :class:`Schema` object.
    """
    if config is None or not config.schema_baseline_path:
        return

    import pathlib

    from lexigram.graphql.schema.diff import SchemaDiffer

    baseline_path = pathlib.Path(config.schema_baseline_path)
    if not baseline_path.exists():
        logger.warning(
            "graphql.schema_diff.baseline_not_found",
            path=str(baseline_path),
        )
        return

    try:
        baseline_sdl = baseline_path.read_text(encoding="utf-8")
        # Parse the SDL into a comparable structure using strawberry's schema
        # introspection.  We convert both to type-name sets via SchemaDiffer.
        from graphql import build_ast_schema, parse

        baseline_schema = build_ast_schema(parse(baseline_sdl))
        differ = SchemaDiffer()
        diff = differ.diff(baseline_schema, current_schema)
    except Exception as exc:  # noqa: BLE001
        logger.warning(
            "graphql.schema_diff.error",
            path=str(baseline_path),
            error=str(exc),
        )
        return

    if not diff.has_changes():
        logger.debug("graphql.schema_diff.no_changes", path=str(baseline_path))
        return

    if diff.breaking:
        for removed in sorted(diff.removed):
            logger.warning(
                "graphql.schema_diff.breaking_removal",
                type_name=removed,
                baseline=str(baseline_path),
            )
    for added in sorted(diff.added):
        logger.debug(
            "graphql.schema_diff.addition",
            type_name=added,
            baseline=str(baseline_path),
        )


__all__ = ["run_schema_diff"]

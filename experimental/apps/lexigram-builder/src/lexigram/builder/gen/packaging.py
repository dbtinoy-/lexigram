"""What the generated ``pyproject.toml`` has to say about dependencies.

Two questions the writer used to answer inline: which extras the drawn field
types drag in, and where the framework sits relative to a generated project.
Both are properties of the emitted project rather than of the writer, and
both are asserted by golden snapshots, so they get a named home.
"""

from __future__ import annotations

from lexigram.builder.graph.models import EntityConfig

__all__ = ["FRAMEWORK_REPO_REL", "extra_dependencies"]

# Generated projects live at <playground>/projects/<app>. The framework is
# vendored as a git submodule at <playground>/lexigram, so from a generated
# project's root two parent hops reach the playground root and the framework
# is at "../../lexigram". Absolute framework-root overrides (tmp-dir runs)
# take precedence (see ``ProjectWriter._monorepo_root``).
FRAMEWORK_REPO_REL = "../../lexigram"


def extra_dependencies(
    entities: list[EntityConfig], uploads: bool = False
) -> tuple[str, ...]:
    """Pinned extra deps required by the field types used in *entities*.

    The framework's Pydantic models rely on optional extras (e.g.
    ``EmailStr`` needs ``email-validator``); surface them in the
    generated pyproject so ``uv sync`` pulls them and the generated
    app imports cleanly.
    """
    field_types = {f.type for entity in entities for f in entity.fields}
    deps: list[str] = []
    if "email" in field_types:
        deps.append("email-validator>=2.0.0")
    if uploads:
        # starlette's request.form() multipart parsing needs it.
        deps.append("python-multipart>=0.0.9")
    return tuple(deps)

"""Contract emission: Pydantic DTO modules + controller payload swaps.

The framework has no DTO/contract generator (Workstream C in
docs/BACKEND_FRAMEWORK_PLANS.md), so the builder emits everything itself,
mirroring the guard-chain / rate-limit builder-side pattern:

1. :func:`emit_contract_module` — renders ``src/app/contracts/<name>.py``
   declaring ``<Pascal>Request`` / ``<Pascal>Response`` Pydantic models
   from the contract's ``fields`` (same field-type grammar as entities,
   reusing ``model_postprocess`` annotations/imports).
2. :func:`apply_contract` — rewrites a generated controller so the ops
   wired to a contract validate payloads with ``<Pascal>Request`` instead
   of the entity's auto-derived ``<Entity>Create``/``<Entity>Update`` and
   pass responses through ``<Pascal>Response.model_validate(...)``
   (shape enforcement; handlers still return JSON-safe dicts, matching
   the framework's ``_to_dict`` response pipeline).

All transforms are deterministic and best-effort: a controller whose text
does not match the expected shapes is returned unchanged rather than
corrupted.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

from lexigram.builder.gen.emitters.model_postprocess import (
    _FIELD_ANNOTATIONS,
    _IMPORT_SPECS,
)
from lexigram.builder.graph.models import ContractConfig

# Per-op handler payload lines rendered by the framework controller
# template (post reconcile_controller, which guarantees this exact shape
# for create/update).
_PAYLOAD_LINE = re.compile(
    r"^(?P<indent>\s+)payload = (?P<model>[A-Za-z_][A-Za-z0-9_]*)\(\*\*data\)\s*$",
    re.MULTILINE,
)

# Single-item responses: `return _to_dict(created)` / `(updated)` / `(item)`.
_ITEM_RETURN = re.compile(
    r"^(?P<indent>\s+)return _to_dict\((?P<var>[a-z_][a-z0-9_]*)\)\s*$",
    re.MULTILINE,
)

# List responses: `return {\n "items": [_to_dict(item) for item in items], ...`.
# Anchored to the comprehension tail: a bare `_to_dict(item)` also occurs in
# the get handler's single-item return (already wrapped by _ITEM_RETURN), and
# an unanchored pattern here would double-wrap it (see test_apply_contract_...).
_LIST_ITEM = re.compile(
    r"_to_dict\((?P<var>item)\)(?=\s+for\s+item\s+in\s+items\])"
)


@dataclass(frozen=True, slots=True)
class ContractBinding:
    """A contract bound to one controller op (keyed by op in
    :class:`ControllerContract`); name/direction drive the swap."""

    contract: ContractConfig

    @property
    def pascal(self) -> str:
        return "".join(p.capitalize() for p in self.contract.name.split("_"))


@dataclass(frozen=True, slots=True)
class ControllerContract:
    """Contract wiring for one entity's controller.

    ``by_op`` maps a CRUD op to the contract bound on the route that
    serves it (first wiring wins when several routes serve the same op).
    """

    by_op: dict[str, ContractBinding]

    @property
    def wired(self) -> bool:
        return bool(self.by_op)


def _pascal(name: str) -> str:
    return "".join(p.capitalize() for p in name.split("_"))


def emit_contract_module(config: ContractConfig) -> str:
    """Render ``src/app/contracts/<name>.py`` for *config*."""
    pascal = _pascal(config.name)
    models: list[tuple[str, str]] = []  # (class name, role)
    if config.direction in ("request", "both"):
        models.append((f"{pascal}Request", "request"))
    if config.direction in ("response", "both"):
        models.append((f"{pascal}Response", "response"))

    # Field lines + the imports their annotations need.
    datetime_members: set[str] = set()
    pydantic_names: set[str] = {"BaseModel"}
    std_lines: set[str] = set()
    field_blocks: list[str] = []
    for field_name, field_type in config.fields:
        base = _FIELD_ANNOTATIONS.get(field_type, "str")
        spec = _IMPORT_SPECS.get(base)
        if spec:
            kind, stmt = spec
            if kind == "datetime":
                datetime_members.add(stmt)
            elif kind == "pydantic":
                pydantic_names.add(stmt.rsplit(" ", 1)[-1])
            elif kind == "std" or kind == "typing":
                std_lines.add(stmt)
        field_blocks.append(f"    {field_name}: {base}")

    import_lines = ["from __future__ import annotations"]
    if datetime_members:
        std_lines.add(
            "from datetime import " + ", ".join(sorted(datetime_members))
        )
    if std_lines:
        import_lines.append("")
        import_lines.extend(sorted(std_lines))
    import_lines.append("")
    import_lines.append(
        "from pydantic import " + ", ".join(sorted(pydantic_names))
    )

    note = config.description or f"Payload schema for {config.name}."
    entity_note = (
        f" Shapes the {config.entity} payload." if config.entity else ""
    )
    direction_note = {
        "request": "Requests replace the entity's auto-derived "
        "<Entity>Create/<Entity>Update DTOs on wired routes.",
        "response": "Responses wrap handler output so wired routes return "
        "exactly this shape (still JSON-safe dicts).",
        "both": "Requests replace the entity's auto-derived DTOs; responses "
        f"are validated into {pascal}Response on wired routes.",
    }[config.direction]

    class_blocks: list[str] = []
    for class_name, role in models:
        body = "\n".join(field_blocks) if field_blocks else "    pass"
        note_plain = note.rstrip(".")
        class_blocks.append(
            f"class {class_name}(BaseModel):\n"
            f'    """{role.capitalize()} model — {note_plain}.{entity_note}"""\n'
            f"\n"
            f"{body}\n"
        )

    return (
        "# generated by lexigram-builder - do not edit\n"
        f'"""{config.name} contract DTOs.\n'
        "\n"
        f"{note}\n"
        "\n"
        f"{direction_note}\n"
        '"""\n'
        "\n"
        + "\n".join(import_lines)
        + "\n\n\n"
        + "\n\n".join(class_blocks)
    )


def apply_contract(text: str, wiring: ControllerContract) -> str:
    """Swap auto-derived DTOs for contract models in a controller source.

    Request-direction contracts replace the ``payload = <Entity>Create/
    Update(**data)`` lines; response-direction contracts wrap
    ``return _to_dict(...)`` (single item) and the ``items`` comprehension
    (list) in ``<Pascal>Response.model_validate(...).model_dump()``.
    """
    if not wiring.wired:
        return text

    # ── imports ──────────────────────────────────────────────────────
    contract_imports: list[str] = []
    for binding in wiring.by_op.values():
        names: list[str] = []
        if binding.contract.direction in ("request", "both"):
            names.append(f"{binding.pascal}Request")
        if binding.contract.direction in ("response", "both"):
            names.append(f"{binding.pascal}Response")
        if not names:
            continue
        line = f"from app.contracts.{binding.contract.name} import " + ", ".join(names)
        if line not in contract_imports:
            contract_imports.append(line)
    if contract_imports:
        text = _ensure_contract_imports(text, contract_imports)

    # ── request payload swaps (create/update ops only) ───────────────
    def _swap_payload(match: re.Match[str]) -> str:
        indent = match.group("indent")
        model = match.group("model")
        # `<Entity>Create` drives create ops, `<Entity>Update` update ops;
        # a request-direction contract bound to that op replaces the model.
        op = "update" if model.endswith("Update") else "create"
        binding = wiring.by_op.get(op)
        if (
            binding is None
            or binding.contract.direction not in ("request", "both")
        ):
            return match.group(0)
        return f"{indent}payload = {binding.pascal}Request(**data)"

    text = _PAYLOAD_LINE.sub(_swap_payload, text)
    text = _prune_dead_dto_imports(text)

    # ── response validation wraps (per op) ───────────────────────────
    def _wrap(expr: str, op: str) -> str:
        binding = wiring.by_op.get(op)
        if (
            binding is None
            or binding.contract.direction not in ("response", "both")
        ):
            return expr
        return (
            f"{binding.pascal}Response.model_validate({expr})"
            '.model_dump(mode="json")'
        )

    def _swap_item_return(match: re.Match[str]) -> str:
        op = _op_for_var(match.group("var"))
        indent = match.group("indent")
        var = match.group("var")
        wrapped = _wrap(f"_to_dict({var})", op)
        if wrapped == f"_to_dict({var})":
            return match.group(0)
        return f"{indent}return {wrapped}"

    text = _ITEM_RETURN.sub(_swap_item_return, text)

    def _swap_list_item(match: re.Match[str]) -> str:
        wrapped = _wrap("_to_dict(item)", "list")
        if wrapped == "_to_dict(item)":
            return match.group(0)
        return wrapped

    return _LIST_ITEM.sub(_swap_list_item, text)


def _op_for_var(var: str) -> str:
    """Map the template's local variable to its handler op."""
    return {"created": "create", "updated": "update", "item": "get"}.get(
        var, "get"
    )


def _prune_dead_dto_imports(text: str) -> str:
    """Drop ``<Entity>Create``/``<Entity>Update`` import names the swap
    orphaned (the docstring mentions them too, so usage means *called*)."""
    match = re.search(
        r"^from app\.models\.(?P<module>[a-z0-9_]+) "
        r"import (?P<names>[A-Za-z0-9_, ]+)$",
        text,
        re.MULTILINE,
    )
    if match is None:
        return text
    names = [n.strip() for n in match.group("names").split(",") if n.strip()]
    # Usage without the import line itself: a real call site.
    without_line = (
        text[: text.rfind("\n", 0, match.start())] + text[match.end():]
    )
    kept = [n for n in names if re.search(rf"\b{n}\s*\(", without_line)]
    if kept == names:
        return text
    line_start = text.rfind("\n", 0, match.start()) + 1
    if not kept:
        # Drop the whole line including its trailing newline.
        return text[:line_start] + text[match.end() + 1 :]
    return (
        text[:line_start]
        + f"from app.models.{match.group('module')} import "
        + ", ".join(kept)
        + text[match.end():]
    )


def _ensure_contract_imports(text: str, import_lines: list[str]) -> str:
    """Insert the ``app.contracts`` imports after the models import."""
    joined = "\n".join(import_lines)
    if all(line in text for line in import_lines):
        return text
    match = re.search(
        r"^from app\.models\.[a-z0-9_]+ import [^\n]+$", text, re.MULTILINE
    )
    if match is None:
        match = re.search(
            r"^from __future__ import annotations$", text, re.MULTILINE
        )
        if match is None:
            return text
        end = match.end()
        return text[:end] + "\n\n" + joined + text[end:]
    end = match.end()
    return text[:end] + "\n" + joined + text[end:]

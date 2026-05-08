"""Alpine-driven query-builder organism with recursive AND/OR groups.

The :class:`QueryBuilder` renders a constraint tree editor (rules + nested
``AND``/``OR`` groups) and serializes the tree to a JSON block model in a
hidden form field.  The block model is the transport contract with
``lexigram.search.filterset.BlockQueryTranslator`` (which lowers it to
``SafeSearchQuery``) — see the Filament-parity design doc 05 part 2.

Block model JSON::

    {
      "logic": "AND",
      "rules": [
        {"field": "status", "operator": "eq", "value": "active"},
        {"logic": "OR", "rules": [{"field": "score", "operator": "gte", "value": 80}]}
      ]
    }

Operator keys are lowercase tokens shared with the translator; the labels
below are display-only.  ``lexigram-ui`` is a leaf package and cannot
import lexigram-search, so this list mirrors the translator's
``SUPPORTED_OPERATORS`` — the translator remains the enforcement point.

Nested groups render up to ``max_depth`` levels in the editor; deeper
nesting still round-trips through the serialized JSON, just without
editor controls.
"""

from __future__ import annotations

from typing import Any

from lexigram.serialization import dumps_str
from lexigram.ui.core.base import Component, el

DEFAULT_OPERATORS = ("eq", "neq", "contains", "gt", "gte", "lt", "lte")

OPERATOR_LABELS: dict[str, str] = {
    "eq": "equals",
    "neq": "does not equal",
    "contains": "contains",
    "gt": "is greater than",
    "gte": "is greater than or equal",
    "lt": "is less than",
    "lte": "is less than or equal",
}


class QueryBuilder(Component):
    """
    A recursive constraint-tree editor backed by Alpine.js.

    The component owns a tree of rules and groups in Alpine state and keeps
    a hidden ``<input name=...>`` in sync with the JSON block model.

    Args:
        name: Form field name for the hidden JSON input.
        value: Optional initial block model as a JSON string or dict.
        label: Optional field label rendered above the editor.
        fields: Optional field catalog — a list of dicts with
            ``name``/``label``/``type`` (``text``, ``number`` or ``select``)
            and, for ``select`` fields, ``options`` (strings or
            ``{"value", "label"}`` pairs).  When omitted, the field is typed
            as free text.
        operators: Optional ordered subset of the shared block operators.
            Defaults to ``("eq", "neq", "contains", "gt", "gte", "lt", "lte")``.
        max_depth: How many nested group levels the editor renders.
            Defaults to 4.
    """

    def __init__(
        self,
        name: str,
        value: str | dict[str, Any] | None = None,
        label: str | None = None,
        fields: list[dict[str, Any]] | None = None,
        operators: tuple[str, ...] | None = None,
        max_depth: int = 4,
        **props: Any,
    ) -> None:
        super().__init__(
            name=name,
            label=label,
            value=value,
            fields=fields,
            operators=operators,
            max_depth=max_depth,
            **props,
        )
        self.name = name
        self.label = label
        self.fields = self._normalize_fields(fields or [])
        self.operators = tuple(operators) if operators else DEFAULT_OPERATORS
        self.max_depth = max(max_depth, 1)

        self.tree, self.next_id = self._build_tree(value)

    # ------------------------------------------------------------------
    # Initial-state normalisation
    # ------------------------------------------------------------------

    @staticmethod
    def _normalize_fields(fields: list[dict[str, Any]]) -> list[dict[str, Any]]:
        """Validate and normalise the caller-supplied field catalog."""
        normalized: list[dict[str, Any]] = []
        for field in fields:
            if not field.get("name") or not field.get("label"):
                raise ValueError("each query-builder field requires 'name' and 'label'")
            entry: dict[str, Any] = {
                "name": str(field["name"]),
                "label": str(field["label"]),
                "type": field.get("type", "text"),
            }
            if entry["type"] == "select":
                options = field.get("options") or []
                entry["options"] = [
                    o if isinstance(o, dict) else {"value": str(o), "label": str(o)}
                    for o in options
                ]
            normalized.append(entry)
        return normalized

    def _build_tree(
        self, value: str | dict[str, Any] | None
    ) -> tuple[dict[str, Any], int]:
        """Convert a block model (dict or JSON string) into an Alpine node tree."""
        counter = 0

        def node_for(entry: dict[str, Any]) -> dict[str, Any]:
            nonlocal counter
            counter += 1
            node_id = counter
            if "field" in entry or "operator" in entry:
                return {
                    "id": node_id,
                    "kind": "rule",
                    "field": entry.get("field", ""),
                    "operator": entry.get("operator", self.operators[0]),
                    "value": entry.get("value"),
                }
            return {
                "id": node_id,
                "kind": "group",
                "logic": entry.get("logic", "AND"),
                "rules": [node_for(child) for child in (entry.get("rules") or [])],
            }

        if value is None:
            return {"id": 1, "kind": "group", "logic": "AND", "rules": []}, 2
        if isinstance(value, str):
            from lexigram.serialization import loads_str

            try:
                value = loads_str(value)
            except (ValueError, TypeError):
                value = None
        if not isinstance(value, dict):
            return {"id": 1, "kind": "group", "logic": "AND", "rules": []}, 2

        root = node_for(value)
        if root.get("kind") != "group":
            root = {"id": 1, "kind": "group", "logic": "AND", "rules": [root]}
        return root, counter + 1

    # ------------------------------------------------------------------
    # Rule row markup (shared at every nesting level)
    # ------------------------------------------------------------------

    def _rule_row(self, var: str) -> Any:
        """Render one editable rule row for the Alpine variable ``var``."""
        controls: list[Any]
        if self.fields:
            controls = [
                el(
                    "select",
                    el(
                        "template",
                        el(
                            "option",
                            x_for="def in fieldOptions",
                            x_bind_value="def.name",
                            x_text="def.label",
                        ),
                    ),
                    x_model=f"{var}.field",
                    class_="qb-field-input bg-background border border-border rounded-md px-2 py-1 text-sm w-44",
                ),
            ]
        else:
            controls = [
                el(
                    "input",
                    type="text",
                    x_model=f"{var}.field",
                    placeholder="Field",
                    class_="qb-field-input bg-background border border-border rounded-md px-2 py-1 text-sm w-44",
                ),
            ]

        controls.append(
            el(
                "select",
                el(
                    "template",
                    el(
                        "option",
                        x_for="op in operatorOptions",
                        x_bind_value="op.value",
                        x_text="op.label",
                    ),
                ),
                x_model=f"{var}.operator",
                class_="qb-operator-input bg-background border border-border rounded-md px-2 py-1 text-sm w-44",
            ),
        )

        controls.extend(
            [
                el(
                    "template",
                    el(
                        "select",
                        el(
                            "template",
                            el(
                                "option",
                                x_for="opt in optionsFor(" + var + ")",
                                x_bind_value="opt.value",
                                x_text="opt.label",
                            ),
                        ),
                        x_model=f"{var}.value",
                        class_="qb-value-input bg-background border border-border rounded-md px-2 py-1 text-sm w-44",
                    ),
                    x_if=f"inputTypeFor({var}) === 'select'",
                ),
                el(
                    "template",
                    el(
                        "input",
                        x_bind_type=f"inputTypeFor({var})",
                        x_model=f"{var}.value",
                        class_="qb-value-input bg-background border border-border rounded-md px-2 py-1 text-sm w-44",
                    ),
                    x_if=f"inputTypeFor({var}) !== 'select'",
                ),
                el(
                    "button",
                    el("i", class_="fas fa-trash text-destructive"),
                    type="button",
                    x_on_click=f"removeNode({var}.id)",
                    title="Remove rule",
                    class_="p-1 hover:bg-accent rounded",
                ),
            ]
        )

        return el(
            "div",
            *controls,
            class_="qb-rule flex items-center gap-2 border border-border rounded-md bg-card px-2 py-1.5 mb-1.5",
        )

    # ------------------------------------------------------------------
    # Group panel markup (recursive)
    # ------------------------------------------------------------------

    def _group_panel(self, depth: int, var: str, removable: bool) -> Any:
        """Render one group panel for the Alpine variable ``var``.

        ``depth`` is how many further nesting levels the editor renders;
        ``removable`` adds a delete button for non-root groups.
        """
        header = [
            el(
                "button",
                "AND",
                type="button",
                x_on_click=f"setLogic({var}.id, 'AND')",
                x_bind_class=f"{var}.logic === 'AND' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'",
                class_="qb-logic-toggle px-2 py-0.5 rounded text-xs font-semibold",
            ),
            el(
                "button",
                "OR",
                type="button",
                x_on_click=f"setLogic({var}.id, 'OR')",
                x_bind_class=f"{var}.logic === 'OR' ? 'bg-primary text-primary-foreground' : 'bg-muted text-muted-foreground'",
                class_="qb-logic-toggle px-2 py-0.5 rounded text-xs font-semibold",
            ),
        ]
        if removable:
            header.append(
                el(
                    "button",
                    el("i", class_="fas fa-trash text-destructive"),
                    type="button",
                    x_on_click=f"removeNode({var}.id)",
                    title="Remove group",
                    class_="p-1 hover:bg-accent rounded ml-auto",
                ),
            )

        child_var = f"n{depth}"
        body: list[Any] = [
            el(
                "template",
                el(
                    "div",
                    el(
                        "template",
                        self._rule_row(child_var),
                        x_if=f"{child_var}.kind === 'rule'",
                    ),
                    el(
                        "template",
                        (
                            self._group_panel(depth - 1, child_var, removable=True)
                            if depth > 1
                            else el(
                                "div",
                                "Nested group (collapsed beyond editor depth)",
                                class_="text-xs text-muted-foreground border border-dashed border-border rounded-md px-2 py-1",
                            )
                        ),
                        x_if=f"{child_var}.kind === 'group'",
                    ),
                ),
                x_for=f"{child_var} in {var}.rules",
                key=f"{child_var}.id",
            ),
            el(
                "div",
                el(
                    "button",
                    el("i", class_="fas fa-plus mr-1"),
                    "Rule",
                    type="button",
                    x_on_click=f"addRule({var}.id)",
                    class_="inline-flex items-center px-2 py-1 border border-dashed border-border rounded text-xs text-foreground bg-card hover:bg-accent",
                ),
                el(
                    "button",
                    el("i", class_="fas fa-layer-group mr-1"),
                    "Group",
                    type="button",
                    x_on_click=f"addGroup({var}.id, 'AND')",
                    class_="inline-flex items-center px-2 py-1 border border-dashed border-border rounded text-xs text-foreground bg-card hover:bg-accent",
                ),
                class_="flex gap-2",
            ),
        ]

        return el(
            "div",
            el("div", *header, class_="flex items-center gap-1 mb-2"),
            *body,
            class_="qb-group border border-border rounded-lg bg-muted/40 p-3 mb-2",
        )

    # ------------------------------------------------------------------
    # Component render
    # ------------------------------------------------------------------

    def render(self) -> Any:
        """Render the query builder with Alpine state and a hidden JSON input."""
        operator_options = [
            {"value": op, "label": OPERATOR_LABELS.get(op, op)} for op in self.operators
        ]

        x_data = {
            "tree": self.tree,
            "nextId": self.next_id,
            "fieldOptions": self.fields,
            "operatorOptions": operator_options,
            "findGroup(nodes, id)": """
                const queue = [...nodes];
                while (queue.length) {
                    const n = queue.shift();
                    if (n.id === id) return n;
                    if (n.kind === 'group') queue.push(...n.rules);
                }
                return null;
            """,
            "addRule(groupId)": """
                const g = this.findGroup(this.tree.rules, groupId);
                if (!g) return;
                g.rules.push({
                    id: this.nextId++,
                    kind: 'rule',
                    field: this.fieldOptions[0] ? this.fieldOptions[0].name : '',
                    operator: this.operatorOptions[0] ? this.operatorOptions[0].value : 'eq',
                    value: null,
                });
            """,
            "addGroup(groupId, logic)": """
                const g = this.findGroup(this.tree.rules, groupId);
                if (!g) return;
                g.rules.push({id: this.nextId++, kind: 'group', logic: logic, rules: []});
            """,
            "removeNode(nodeId)": """
                const prune = (nodes) => {
                    for (let i = nodes.length - 1; i >= 0; i--) {
                        if (nodes[i].id === nodeId) { nodes.splice(i, 1); return true; }
                        if (nodes[i].kind === 'group' && prune(nodes[i].rules)) return true;
                    }
                    return false;
                };
                prune(this.tree.rules);
            """,
            "setLogic(groupId, logic)": """
                const g = this.findGroup(this.tree.rules, groupId);
                if (g) g.logic = logic;
            """,
            "inputTypeFor(node)": """
                const def = this.fieldOptions.find(f => f.name === node.field);
                if (!def) return 'text';
                if (def.type === 'number' || def.type === 'integer' || def.type === 'float') return 'number';
                if (def.type === 'select') return 'select';
                return 'text';
            """,
            "optionsFor(node)": """
                const def = this.fieldOptions.find(f => f.name === node.field);
                return def && def.type === 'select' ? (def.options || []) : [];
            """,
            "serialize()": """
                const ser = (n) => {
                    if (n.kind === 'rule') return {field: n.field, operator: n.operator, value: n.value};
                    return {logic: n.logic, rules: (n.rules || []).map(ser)};
                };
                return JSON.stringify(ser(this.tree));
            """,
        }

        return el(
            "div",
            el(
                "input",
                type="hidden",
                name=self.name,
                x_bind_value="serialize()",
            ),
            (
                el(
                    "label",
                    self.label,
                    class_="block text-sm font-medium mb-1.5 text-foreground",
                )
                if self.label
                else None
            ),
            self._group_panel(self.max_depth, "tree", removable=False),
            x_data=dumps_str(x_data),
            class_="lex-query-builder w-full",
        )


__all__ = ["DEFAULT_OPERATORS", "OPERATOR_LABELS", "QueryBuilder"]

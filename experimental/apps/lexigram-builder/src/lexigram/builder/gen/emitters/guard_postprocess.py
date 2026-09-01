"""Guard-chain emission: reconcile guard scaffolds and decorate controllers.

Three transforms, one per artifact the guard chain (auth / role / rate_limit
canvas nodes) produces — see Workstream B in docs/BACKEND_FRAMEWORK_PLANS.md:

1. :func:`reconcile_guard` — the lexigram-auth ``guard`` generator imports
   both ``RoleGuard`` and ``PermissionGuard`` unconditionally but only
   renders the class matching its ``type`` option, so the unused import is
   dropped (F401) for types that don't reference it.
2. :func:`apply_guards` — applies ``@require_auth()`` /
   ``@require_roles(...)`` (from ``lexigram.auth.web``) to the controller
   handlers of guarded routes, directly below the route decorator and above
   the ``async def``. Idempotent; no-op when a handler is already guarded.
3. :func:`emit_rate_limit_module` + :func:`emit_rate_limit_middleware` —
   the framework has no per-route throttle primitive, so rate_limit nodes
   emit the policy module (strategy/window/max constants + guarded paths)
   plus an ASGI middleware that enforces it (429 + Retry-After).

All transforms are deterministic and best-effort: a framework template that
changes shape degrades to "no decoration" rather than corrupting output.
"""

from __future__ import annotations

from dataclasses import dataclass, field
import re

from lexigram.builder.graph.models import RateLimitConfig

# A controller handler definition, e.g. `    async def create(self, request)`.
_HANDLER_DEF = re.compile(
    r"^(?P<indent>[ ]{4})async def (?P<op>create|get|list|update|delete)\(",
    re.MULTILINE,
)

# The route-decorator import line every generated controller carries.
_CONTROLLER_IMPORT_LINE = re.compile(
    r"^from lexigram\.web import Controller.*$", re.MULTILINE
)


@dataclass(frozen=True, slots=True)
class ControllerGuards:
    """Guard wiring for one entity's controller.

    Attributes:
        ops: CRUD ops guarded by authentication only (routes wired to an
            auth node without a role) — they render ``@require_auth()``.
        roles_by_op: Role names accepted per op (routes wired to role
            nodes) — these ops render ``@require_roles(...)`` instead,
            which implies authentication.
    """

    ops: frozenset[str] = frozenset()
    roles_by_op: dict[str, tuple[str, ...]] = field(default_factory=dict)

    @property
    def guarded(self) -> bool:
        return bool(self.ops or self.roles_by_op)


def reconcile_guard(text: str) -> str:
    """Drop imported names the generated guard module never uses.

    The ``guard`` template imports ``PermissionGuard``/``RoleGuard`` on
    every render but only emits the class matching ``type``; a name whose
    only occurrence is its import is removed (the whole import line when it
    becomes empty).
    """
    for name in ("PermissionGuard", "RoleGuard"):
        if text.count(name) == 1:
            text = re.sub(
                rf"^from lexigram\.auth\.web\.guards import ([^,\n]*, )?{name}"
                rf"(, )?([^,\n]*)$",
                lambda m: _rejoin_import(m.group(1), m.group(3)),
                text,
                flags=re.MULTILINE,
            )
    return text


def _rejoin_import(head: str | None, tail: str | None) -> str:
    """Rebuild an import line after removing one name from it."""
    parts = [p.strip() for p in (head or "").split(",") if p.strip()]
    if tail and tail.strip():
        parts.append(tail.strip())
    if not parts:
        return ""
    return f"from lexigram.auth.web.guards import {', '.join(parts)}"


def apply_guards(text: str, guards: ControllerGuards) -> str:
    """Decorate guarded handlers in a generated controller source.

    Decorators are resolved per op so two routes on one entity can carry
    different guards (e.g. ``create`` role-guarded, ``list`` auth-only).
    Roles win over plain auth (``require_roles`` authenticates *and*
    authorizes — a role wired to the route collapses the auth requirement,
    matching "role → auth collapses to the auth guard" in the plan).
    """
    if not guards.guarded:
        return text

    def _decorator(op: str) -> str:
        roles = guards.roles_by_op.get(op)
        if roles:
            quoted = ", ".join(f'"{role}"' for role in roles)
            return f"    @require_roles({quoted})"
        return "    @require_auth()"

    text = _ensure_guard_import(
        text, need_roles=any(guards.roles_by_op.values())
    )

    out: list[str] = []
    for line in text.split("\n"):
        match = _HANDLER_DEF.match(line)
        already = bool(out) and out[-1].lstrip().startswith(
            ("@require_auth", "@require_roles")
        )
        if match is not None and not already:
            op = match.group("op")
            if op in guards.ops or op in guards.roles_by_op:
                out.append(_decorator(op))
        out.append(line)
    return "\n".join(out)


def _ensure_guard_import(text: str, *, need_roles: bool) -> str:
    """Add the ``lexigram.auth.web`` guard imports once, after the
    controller base import line."""
    names = ["require_roles"] if need_roles else ["require_auth"]
    if all(re.search(rf"^from lexigram\.auth\.web import .*\b{n}\b", text, re.MULTILINE) for n in names):
        return text
    import_line = (
        "from lexigram.auth.web import require_auth, require_roles\n"
        if need_roles
        else "from lexigram.auth.web import require_auth\n"
    )
    match = _CONTROLLER_IMPORT_LINE.search(text)
    if match is None:
        # Template drifted — prepend after the future import to stay safe.
        return text.replace(
            "from __future__ import annotations\n",
            "from __future__ import annotations\n\n" + import_line,
            1,
        )
    end = match.end()
    return text[:end] + "\n" + import_line.rstrip("\n") + text[end:]


def emit_rate_limit_middleware(
    policies: list[tuple[RateLimitConfig, tuple[str, ...]]],
) -> str:
    """Render ``src/app/middleware/rate_limit.py`` (nodes plan N2.2).

    Enforces the emitted policy modules in-process: policy constants are
    imported from ``src/app/policies/*_rate_limit.py`` so definition and
    enforcement cannot drift. Counters are per-process — sufficient for the
    generated starter (single worker); a shared store is the documented
    multi-worker follow-up.
    """
    imports: list[str] = []
    entries: list[str] = []
    for config, _paths in policies:
        alias = config.name.upper()
        module = f"app.policies.{config.name}_rate_limit"
        # One import statement per aliased name — ruff isort's default
        # (combine-as-imports=false) wants exactly this form.
        for const in ("APPLIES_TO", "KEY_BY", "MAX_REQUESTS", "STRATEGY", "WINDOW_SECONDS"):
            imports.append(f"from {module} import {const} as {alias}_{const}")
        entries.append(
            "    _Policy(\n"
            f'        name="{config.name}",\n'
            f"        strategy={alias}_STRATEGY,\n"
            f"        window_seconds={alias}_WINDOW_SECONDS,\n"
            f"        max_requests={alias}_MAX_REQUESTS,\n"
            f"        key_by={alias}_KEY_BY,\n"
            f"        applies_to={alias}_APPLIES_TO,\n"
            "    ),"
        )
    import_block = "\n".join(imports)
    entries_block = "\n".join(entries)
    return (
        "# generated by lexigram-builder - do not edit\n"
        '"""In-process rate limiting for wired routes (builder-generated).\n'
        "\n"
        "Enforces the policy constants from ``src/app/policies/*_rate_limit.py``\n"
        "so the definition and the enforcement cannot drift. Strategies:\n"
        "``fixed_window``, ``sliding_window``, ``token_bucket``; the throttle\n"
        "key is derived from ``key_by`` (ip / user / api_key / custom headers).\n"
        "\n"
        "Counters live in this process (monotonic clock). Fine for the single-\n"
        "worker starter; wire a shared store (e.g. Redis) for multi-worker\n"
        "deployments.\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        "from collections import deque\n"
        "from dataclasses import dataclass\n"
        "import json\n"
        "from time import monotonic\n"
        "\n"
        + import_block
        + "\n"
        "\n"
        "\n"
        "@dataclass(frozen=True, slots=True)\n"
        "class _Policy:\n"
        "    name: str\n"
        "    strategy: str\n"
        "    window_seconds: int\n"
        "    max_requests: int\n"
        "    key_by: str\n"
        "    applies_to: tuple[str, ...]\n"
        "\n"
        "\n"
        "_POLICIES: tuple[_Policy, ...] = (\n"
        + entries_block
        + "\n"
        ")\n"
        "\n"
        "\n"
        "def _client_key(key_by: str, scope: dict) -> str:\n"
        '    """Derive the throttle key per the policy\'s ``key_by``."""\n'
        '    headers = {\n'
        '        k.decode("latin-1").lower(): v.decode("latin-1")\n'
        '        for k, v in scope.get("headers", ())\n'
        "    }\n"
        '    if key_by == "api_key" and headers.get("x-api-key"):\n'
        '        return "key:" + headers["x-api-key"]\n'
        '    if key_by == "custom" and headers.get("x-rate-limit-key"):\n'
        '        return "custom:" + headers["x-rate-limit-key"]\n'
        '    if key_by == "user" and headers.get("authorization"):\n'
        '        return "user:" + headers["authorization"]\n'
        '    client = scope.get("client")\n'
        '    return "ip:" + (client[0] if client else "unknown")\n'
        "\n"
        "\n"
        "class RateLimitMiddleware:\n"
        '    """Throttle requests whose path matches a policy\'s prefixes."""\n'
        "\n"
        "    def __init__(self, app):\n"
        "        self.app = app\n"
        "        self._fixed: dict[str, tuple[int, float]] = {}\n"
        "        self._sliding: dict[str, deque[float]] = {}\n"
        "        self._buckets: dict[str, tuple[float, float]] = {}\n"
        "\n"
        "    async def __call__(self, scope, receive, send):\n"
        '        if scope["type"] != "http" or not _POLICIES:\n'
        "            await self.app(scope, receive, send)\n"
        "            return\n"
        '        path = scope.get("path", "")\n'
        "        policy = next(\n"
        "            (\n"
        "                p\n"
        "                for p in _POLICIES\n"
        "                if any(path.startswith(prefix) for prefix in p.applies_to)\n"
        "            ),\n"
        "            None,\n"
        "        )\n"
        "        if policy is None:\n"
        "            await self.app(scope, receive, send)\n"
        "            return\n"
        '        key = f"{policy.name}:{_client_key(policy.key_by, scope)}"\n'
        "        allowed, retry_after = self._check(policy, key)\n"
        "        if allowed:\n"
        "            await self.app(scope, receive, send)\n"
        "            return\n"
        '        body = json.dumps(\n'
        '            {"error": "rate_limited", "message": "Too many requests"}\n'
        "        ).encode()\n"
        "        await send(\n"
        "            {\n"
        '                "type": "http.response.start",\n'
        '                "status": 429,\n'
        '                "headers": [\n'
        '                    (b"content-type", b"application/json"),\n'
        '                    (b"retry-after", str(max(1, int(retry_after))).encode()),\n'
        "                ],\n"
        "            }\n"
        "        )\n"
        '        await send({"type": "http.response.body", "body": body})\n'
        "\n"
        "    def _check(self, policy: _Policy, key: str) -> tuple[bool, float]:\n"
        '        """Return ``(allowed, retry_after_seconds)`` for one request."""\n'
        "        now = monotonic()\n"
        '        if policy.strategy == "sliding_window":\n'
        "            hits = self._sliding.setdefault(key, deque())\n"
        "            while hits and now - hits[0] >= policy.window_seconds:\n"
        "                hits.popleft()\n"
        "            if len(hits) >= policy.max_requests:\n"
        "                return False, hits[0] + policy.window_seconds - now\n"
        "            hits.append(now)\n"
        "            return True, 0.0\n"
        '        if policy.strategy == "token_bucket":\n'
        "            refill = policy.max_requests / max(1, policy.window_seconds)\n"
        "            tokens, last = self._buckets.get(key, (float(policy.max_requests), now))\n"
        "            tokens = min(policy.max_requests, tokens + (now - last) * refill)\n"
        "            if tokens < 1.0:\n"
        "                self._buckets[key] = (tokens, now)\n"
        "                return False, (1.0 - tokens) / refill\n"
        "            self._buckets[key] = (tokens - 1.0, now)\n"
        "            return True, 0.0\n"
        "        # fixed_window (default)\n"
        "        start, count = self._fixed.get(key, (now, 0))\n"
        "        if now - start >= policy.window_seconds:\n"
        "            start, count = now, 0\n"
        "        if count >= policy.max_requests:\n"
        "            return False, policy.window_seconds - (now - start)\n"
        "        self._fixed[key] = (start, count + 1)\n"
        "        return True, 0.0\n"
    )


def emit_rate_limit_module(
    config: RateLimitConfig,
    *,
    paths: tuple[str, ...],
    doc: str = "",
) -> str:
    """Render a rate-limit policy module.

    The constants here are the single definition the generated middleware
    (:func:`emit_rate_limit_middleware`) enforces; the docstring documents
    the module for hand-rolled consumers too.
    """
    name = config.name
    strategy = config.strategy
    window = config.window_seconds
    max_requests = config.max_requests
    key_by = config.key_by
    if paths:
        applies = "\n" + "\n".join(f'    "{p}",' for p in paths) + "\n"
    else:
        applies = "\n    # (no wired routes)\n"
    note = doc or f"Throttling policy for {name}."
    return (
        "# generated by lexigram-builder - do not edit\n"
        f'"""{name} rate-limit policy.\n'
        "\n"
        f"{note}\n"
        "\n"
        "These constants are the policy definition; the generated\n"
        "src/app/middleware/rate_limit.py enforces them for the wired paths.\n"
        "Hand-rolled consumers can import the same constants.\n"
        '"""\n'
        "\n"
        "from __future__ import annotations\n"
        "\n"
        f'STRATEGY = "{strategy}"\n'
        f"WINDOW_SECONDS = {window}\n"
        f"MAX_REQUESTS = {max_requests}\n"
        f'KEY_BY = "{key_by}"\n'
        "\n"
        "# Route path prefixes this policy throttles:\n"
        f"APPLIES_TO = ({applies})\n"
    )

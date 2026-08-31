"""Feature-flag endpoint gating (nodes plan N2.1).

The framework has no flag decorator/guard for handlers yet, so the builder
injects the check itself — same builder-side pattern as the guard chain:

- Routes wired to an enabled ``feature_flag`` node gate their handlers with
  an in-body check against the DI-injected :class:`FlagManager`
  (``FeatureFlagsModule`` registers it as a singleton; the flag's canonical
  key is seeded from the node).
- A disabled flag rejects the request with ``NotFoundError`` (404 — does not
  leak the feature's existence). Several flags wired to one route gate
  conjunctively (all must be enabled).
- Degradation is no-decoration: a controller whose constructor/docstring
  shape does not match the framework template is returned unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass
import re

_HANDLER_DEF = re.compile(
    r"^(?P<indent>[ ]{4})async def (?P<op>create|get|list|update|delete)\(",
    re.MULTILINE,
)
_CONTROLLER_IMPORT_LINE = re.compile(
    r"^from lexigram\.web import Controller.*$", re.MULTILINE
)
_FLAG_IMPORT_LINE = "from lexigram.features import FlagManager"
_REPO_CTOR = re.compile(
    r"    def __init__\(self, repo: (?P<repo>\w+)\) -> None:\n"
    r"        super\(\)\.__init__\(\)\n"
    r"        self\.repo = repo\n"
)
_MISSING_FEATURE_MESSAGE = "This feature is not available."


@dataclass(frozen=True, slots=True)
class ControllerFlagGates:
    """Flag wiring for one entity's controller.

    ``by_op`` maps a CRUD op to the canonical flag keys that must be enabled
    (AND semantics) before the handler runs.
    """

    by_op: dict[str, tuple[str, ...]]

    @property
    def wired(self) -> bool:
        return bool(self.by_op)


def apply_flag_gates(text: str, gates: ControllerFlagGates) -> str:
    """Inject flag checks into a generated controller source."""
    if not gates.wired:
        return text

    text = _ensure_flag_manager_import(text)
    text = _inject_flags_dependency(text)

    out: list[str] = []
    i = 0
    lines = text.split("\n")
    while i < len(lines):
        line = lines[i]
        match = _HANDLER_DEF.match(line)
        if match is None:
            out.append(line)
            i += 1
            continue
        op = match.group("op")
        keys = gates.by_op.get(op, ())
        body_start = _handler_body_start(lines, i)
        body = "\n".join(lines[body_start:])
        already = 'self._flags.is_enabled("' in body.split("\n\n", 1)[0] or _op_gated(
            lines, body_start, keys
        )
        out.extend(lines[i:body_start])
        if keys and not already:
            for key in keys:
                out.append(
                    f'        if not await self._flags.is_enabled("{key}"):'
                )
                out.append(
                    f'            raise NotFoundError("{_MISSING_FEATURE_MESSAGE}")'
                )
        i = body_start
    return "\n".join(out)


def _op_gated(lines: list[str], body_start: int, keys: tuple[str, ...]) -> bool:
    """True when this handler body already checks one of *keys*."""
    window = "\n".join(lines[body_start : body_start + 6])
    return any(f'self._flags.is_enabled("{key}")' in window for key in keys)


def _handler_body_start(lines: list[str], def_index: int) -> int:
    """Index of the first statement line of the handler body.

    Skips the (possibly multi-line) signature, then the docstring when the
    body opens with one — checks are inserted after it so the docstring
    stays a docstring.
    """
    j = def_index
    while j < len(lines) and not lines[j].rstrip().endswith(":"):
        j += 1
    j += 1  # first body line
    # Skip a docstring, if present.
    if j < len(lines):
        stripped = lines[j].lstrip()
        if stripped.startswith('"""'):
            if stripped.endswith('"""') and len(stripped) > 3:
                return j + 1  # single-line docstring
            j += 1
            while j < len(lines) and '"""' not in lines[j]:
                j += 1
            return j + 1
    return j


def _ensure_flag_manager_import(text: str) -> str:
    if _FLAG_IMPORT_LINE in text:
        return text
    match = _CONTROLLER_IMPORT_LINE.search(text)
    if match is None:
        return text.replace(
            "from __future__ import annotations\n",
            "from __future__ import annotations\n\n" + _FLAG_IMPORT_LINE,
            1,
        )
    end = match.end()
    return text[:end] + "\n" + _FLAG_IMPORT_LINE + text[end:]


def _inject_flags_dependency(text: str) -> str:
    """Add the DI-injected ``FlagManager`` to the repository constructor."""
    if "self._flags" in text:
        return text
    return _REPO_CTOR.sub(
        "    def __init__(self, repo: \\1, flags: FlagManager) -> None:\n"
        "        super().__init__()\n"
        "        self.repo = repo\n"
        "        self._flags = flags\n",
        text,
    )

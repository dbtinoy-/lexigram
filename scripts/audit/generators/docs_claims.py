"""Audit generator: verify claim-level API facts cited across package docs.

Checks two claim classes that the import audit cannot see:

1. **Environment variables** — every ``LEX_*`` env var mention in a package doc
   must resolve against live configuration classes:

   - ``LEX_<SECTION>__<KEY>`` — core ``LEX_`` prefix plus a ``*Config`` class
     section and (nested) key path, e.g. ``LEX_LOGGING__JSON_FORMAT``.
   - ``LEX_<PACKAGE>__<KEY>`` — extension packages register their own prefix
     (e.g. ``LEX_SQL``) with keys straight from their config classes, e.g.
     ``LEX_SQL__BACKEND__URL``.
   - ``<env_prefix>`` — pydantic ``model_config["env_prefix"]`` families, e.g.
     ``LEX_NOTIFICATION__INBOX__MARK_READ_ON_FETCH``.
   - ``*`` keypath segments are wildcards for list/dict positions
     (``LEX_CACHE__BACKENDS__0__NAME`` matches ``backends.*.name``).
   - Variables read directly by framework code (``os.environ.get("LEX_QUIET")``)
     are whitelisted.
   - ``LEX_ERR_*`` is the error-code namespace, not env vars — ignored.
   - Trailing-``__`` tokens are env-source prefix claims.

2. **Provider priorities** — every ``ProviderPriority.<MEMBER>`` claim must be a
   real member of ``lexigram.contracts.core.provider.ProviderPriority``.
"""

from __future__ import annotations

from dataclasses import dataclass
from dataclasses import fields as dc_fields
import importlib
from pathlib import Path
import re
import types
import typing

from scripts.audit.generators.base import AuditRunResult, MarkdownAuditGenerator

_ENV_TOKEN_RE = re.compile(r"\bLEX_[A-Z][A-Z0-9_]*\b")
_PRIORITY_RE = re.compile(r"ProviderPriority\.([A-Z][A-Z0-9_]*)")
_SECTION_CONFIG_SUFFIX = "Config"
# `LEX_ERR_*` is the error-code namespace (LEX_ERR_<PKG>_<CODE>) — not env vars.
_ERROR_CODE_PREFIX = "LEX_ERR_"
# Trailing-delimiter tokens (`LEX_X__`) are env-source prefix claims.
_PREFIX_TOKEN_SUFFIX = "__"

# Env vars read directly by framework code (never a section/key mapping).
_DIRECT_READ_ENV_VARS = frozenset(
    {
        "LEX_CONFIG",
        "LEX_DEBUG",
        "LEX_ENV",
        "LEX_PROFILE",
        "LEX_QUIET",
    }
)

# Dynamic namespaces: any token under these prefixes is a valid env var.
_DYNAMIC_PREFIXES = (
    # Feature-flag overrides: FeatureFlagsConfig.flag_env_prefix is "LEX_FLAG_".
    "LEX_FLAG_",
)

_PRIORITY_MODULE = "lexigram.contracts.core.provider"
_PRIORITY_ENUM = "ProviderPriority"


@dataclass(frozen=True, slots=True)
class ClaimIssue:
    """A doc claim that did not resolve against the framework."""

    doc: str
    claim: str
    reason: str


def _iter_python_blocks(md_text: str) -> tuple[str, ...]:
    return tuple(
        match.group(1)
        for match in re.finditer(r"```(?:python|py)\s*\n(.*?)```", md_text, re.DOTALL)
    )


def _annotation_names(config_cls: type) -> tuple[str, ...]:
    """Field names from type annotations, excluding ClassVar/private members."""
    try:
        hints = typing.get_type_hints(config_cls)
    except Exception:  # noqa: BLE001 - unresolvable hints degrade gracefully
        return ()
    return tuple(
        name
        for name, ftype in hints.items()
        if not name.startswith("_")
        and typing.get_origin(ftype) is not typing.ClassVar
    )


def _is_config_class(obj: object) -> bool:
    """True for dataclasses, pydantic models, and DomainModel-style configs."""
    if not isinstance(obj, type):
        return False
    try:
        if dc_fields(obj):
            return True
    except TypeError:
        pass
    if getattr(obj, "model_fields", None):
        return True
    return bool(_annotation_names(obj))


def _field_names(config_cls: type) -> tuple[str, ...]:
    """Declared field names for dataclass / pydantic / annotated config classes."""
    fields = getattr(config_cls, "model_fields", ())
    if fields:
        return tuple(fields)
    try:
        own = tuple(f.name for f in dc_fields(config_cls))
    except TypeError:
        return _annotation_names(config_cls)
    if own:
        return own
    return _annotation_names(config_cls)


def _driver_segment(config_cls: type) -> str:
    """Lowercased short name of a driver config class (``StorageS3Config`` -> ``s3``)."""
    name = config_cls.__name__
    if name.endswith("Config"):
        name = name[: -len("Config")]
    for prefix in ("Storage", "Cache", "Backend", "Driver"):
        if name.startswith(prefix):
            name = name[len(prefix) :]
            break
    return name.lower()


def _union_members(ftype: object) -> tuple[object, ...]:
    """Union arguments excluding ``None``; a non-union type is returned as-is."""
    origin = typing.get_origin(ftype)
    if origin is typing.Union or origin is types.UnionType:
        return tuple(
            arg for arg in typing.get_args(ftype) if arg is not type(None)  # noqa: E721
        )
    return (ftype,)


def _sequence_element(ftype: object) -> object | None:
    """Element type of ``list[T]`` / ``tuple[T]`` / ``Sequence[T]``, else None."""
    if typing.get_origin(ftype) in (list, tuple, set, frozenset, typing.Sequence):
        args = typing.get_args(ftype)
        if args:
            return args[0]
    return None


def _mapping_value(ftype: object) -> object | None:
    """Value type of ``dict[str, V]`` / ``Mapping[str, V]``, else None."""
    if typing.get_origin(ftype) in (dict, typing.Mapping):
        args = typing.get_args(ftype)
        if len(args) == 2:
            return args[1]
    return None


def _nested_keypaths(config_cls: type, max_depth: int = 4) -> tuple[str, ...]:
    """All dotted key paths (depth 1..max_depth) reachable from a config class.

    ``*`` segments denote list/dict positions: ``drivers.*.bucket`` or
    ``extra.*`` for scalar-valued mappings (arbitrary keys).
    """

    seen_types: set[int] = set()
    paths: list[str] = []

    def walk(cls: type, prefix: str, depth: int) -> None:
        if depth > max_depth or id(cls) in seen_types:
            return
        seen_types.add(id(cls))
        names = _field_names(cls)
        annotations: dict[str, object] = {}
        try:
            annotations = typing.get_type_hints(cls)
        except Exception:  # noqa: BLE001 - unresolvable hints degrade gracefully
            pass
        for name in names:
            path = f"{prefix}.{name}" if prefix else name
            paths.append(path)
            ftype = annotations.get(name)
            if ftype is None or typing.get_origin(ftype) is typing.ClassVar:
                continue
            for member in _union_members(ftype):
                element = _sequence_element(member)
                if element is not None and _is_config_class(element):
                    walk(element, f"{path}.*", depth + 1)
                    continue
                mapped = _mapping_value(member)
                if mapped is not None:
                    value_members = [
                        m for m in _union_members(mapped) if _is_config_class(m)
                    ]
                    if value_members:
                        for value_cls in value_members:
                            walk(value_cls, f"{path}.*", depth + 1)
                            segment = _driver_segment(value_cls)
                            if segment:
                                walk(value_cls, f"{path}.{segment}", depth + 1)
                    else:
                        paths.append(f"{path}.*")
                    continue
                if _is_config_class(member):
                    walk(member, path, depth + 1)

    walk(config_cls, "", 1)
    return tuple(paths)


def _config_classes(target: object | None) -> tuple[type, ...]:
    """Every config class (dataclass or pydantic) exposed by a module."""
    if target is None:
        return ()
    found: list[type] = []
    for attr_name in dir(target):
        if attr_name.endswith(_SECTION_CONFIG_SUFFIX):
            try:
                attr = getattr(target, attr_name)
            except Exception:  # noqa: BLE001 - lazy __getattr__ may raise
                continue
            if _is_config_class(attr):
                found.append(attr)
    return tuple(found)


def _config_modules(pkg_root: Path, pkg_mod_name: str) -> tuple[str, ...]:
    """Dotted module paths of a package's config-bearing modules.

    Any module whose path contains a ``config`` component or that ends in
    ``config.py`` (e.g. ``lexigram.logging.config``,
    ``lexigram.app.config.models``, ``lexigram.web.security.config``).
    """
    src_dir = pkg_root / "src"
    if not src_dir.is_dir():
        return ()
    modules: list[str] = []
    for py in sorted(src_dir.rglob("*.py")):
        parts = py.relative_to(src_dir).with_suffix("").parts
        if not parts or parts[0] != pkg_mod_name.split(".", 1)[0] or "." in parts[0]:
            continue
        if "config" not in parts:
            continue
        if parts[-1] == "__init__":
            modules.append(".".join(parts[:-1]))
        else:
            modules.append(".".join(parts))
    return tuple(modules)


def _try_import(mod_name: str) -> object | None:
    try:
        return importlib.import_module(mod_name)
    except Exception:  # noqa: BLE001 - optional modules may not import
        return None


def _build_declared_prefixes() -> set[str]:
    """Env prefixes declared as constants in framework source.

    Some packages declare an env prefix constant (``GRAPH_ENV_PREFIX =
    "LEX_WORKFLOW__GRAPH__"``) without wiring it into ``model_config``;
    tokens under a declared prefix are still legitimate claims.
    """
    root = Path(__file__).resolve().parents[3]
    declared: set[str] = set()
    prefix_re = re.compile(
        r'\w*PREFIX\w*\s*(?::\s*\w+\s*)?=\s*["\'](LEX_[A-Z0-9_]+__)["\']'
    )
    for pkg in root.iterdir():
        if not (
            pkg.is_dir()
            and (pkg.name == "lexigram" or pkg.name.startswith("lexigram-"))
        ):
            continue
        src_dir = pkg / "src"
        if not src_dir.is_dir():
            continue
        for py in src_dir.rglob("*.py"):
            try:
                text = py.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if "PREFIX" not in text:
                continue
            declared.update(prefix_re.findall(text))
    # Package-level headers (`LEX_SQL__`) declare a namespace, not specific
    # vars — only sub-section prefixes (`LEX_WORKFLOW__GRAPH__`) count as
    # declared variables.
    return {p for p in declared if p[p.index("LEX_") + 4 :].count("__") >= 2}


def _build_env_validity() -> dict[str, str]:
    """Map valid env vars to their ``section.key`` path.

    Two families cover the framework's env patterns:

    1. Core prefix ``LEX_`` + config-class section: ``LEX_LOGGING__JSON_FORMAT``
       (any package's ``*Config`` class, nested keys joined with ``__``).
    2. Package prefix ``LEX_<PACKAGE>`` + nested key path: extension packages
       register their own prefix (e.g. ``LEX_SQL``) with keys straight from the
       package's config classes (e.g. ``LEX_SQL__BACKEND__URL``).
    """
    validity: dict[str, str] = {}
    packages = sorted(
        path
        for path in Path(__file__).resolve().parents[3].iterdir()
        if path.is_dir()
        and (path.name == "lexigram" or path.name.startswith("lexigram-"))
    )
    for pkg in packages:
        pkg_mod_name = (
            "lexigram" if pkg.name == "lexigram" else pkg.name.replace("-", ".")
        )
        classes = list(_config_classes(_try_import(pkg_mod_name)))
        for mod_path in _config_modules(pkg, pkg_mod_name):
            classes += _config_classes(_try_import(mod_path))
        pkg_short = (
            None
            if pkg.name == "lexigram"
            else pkg.name[len("lexigram-") :].replace("-", "_")
        )
        for config_cls in classes:
            declared_section = getattr(config_cls, "config_section", None)
            section = (
                str(declared_section)
                if declared_section
                else config_cls.__name__[: -len(_SECTION_CONFIG_SUFFIX)].lower()
            )
            model_config = getattr(config_cls, "model_config", None)
            env_prefix = ""
            nested_delimiter = "__"
            if isinstance(model_config, dict):
                env_prefix = str(model_config.get("env_prefix", ""))
                nested_delimiter = str(
                    model_config.get("env_nested_delimiter", "__")
                )
            for keypath in _nested_keypaths(config_cls):
                parts = "__".join(keypath.upper().split("."))
                if env_prefix:
                    validity[f"{env_prefix.upper()}{parts.replace('__', nested_delimiter.upper())}"] = (
                        f"{env_prefix}{keypath}".lower()
                    )
                    continue
                validity[f"LEX_{section.upper()}__{parts}"] = (
                    f"{section}.{keypath}"
                )
                if pkg_short is not None:
                    validity[f"LEX_{pkg_short.upper()}__{parts}"] = (
                        f"{pkg_short}.{keypath}"
                    )
    return validity


def _build_direct_reads() -> set[str]:
    """Env vars read directly by framework source code."""
    root = Path(__file__).resolve().parents[3]
    found: set[str] = set(_DIRECT_READ_ENV_VARS)
    get_re = re.compile(r"os\.environ\.get\(\s*[\"'](LEX_[A-Z0-9_]+)[\"']")
    for pkg in root.iterdir():
        if not (
            pkg.is_dir()
            and (pkg.name == "lexigram" or pkg.name.startswith("lexigram-"))
        ):
            continue
        src_dir = pkg / "src"
        if not src_dir.is_dir():
            continue
        for py in src_dir.rglob("*.py"):
            try:
                text = py.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            found.update(get_re.findall(text))
    return found


def _collect_env_claims(md_text: str) -> tuple[str, ...]:
    """Return every distinct non-error-code ``LEX_*`` token in a doc."""
    seen: set[str] = set()
    for block in _iter_python_blocks(md_text):
        seen.update(_ENV_TOKEN_RE.findall(block))
    for match in _ENV_TOKEN_RE.finditer(md_text):
        seen.add(match.group(0))
    return tuple(sorted(t for t in seen if not t.startswith(_ERROR_CODE_PREFIX)))


def _collect_priority_claims(md_text: str) -> tuple[str, ...]:
    seen: set[str] = set()
    for match in _PRIORITY_RE.finditer(md_text):
        seen.add(match.group(1))
    return tuple(sorted(seen))


def _parts_match(valid_key: str, token: str) -> bool:
    """Part-wise match where ``*`` segments in the validity key match any token part."""
    token_parts = token.split("__")
    valid_parts = valid_key.split("__")
    if len(token_parts) != len(valid_parts):
        return False
    for valid_part, token_part in zip(valid_parts, token_parts, strict=True):
        if valid_part not in ("*", token_part):
            return False
    return True


def _prefix_parts_match(valid_key: str, token_prefix: str) -> bool:
    """True when a token prefix matches a validity key part-wise (wildcard-aware)."""
    token_parts = token_prefix.split("__")
    key_parts = valid_key.split("__")
    if len(key_parts) < len(token_parts):
        return False
    for token_part, key_part in zip(token_parts, key_parts):
        if key_part != "*" and key_part != token_part:
            return False
    return True


def _verify_env_var(
    token: str,
    validity: dict[str, str],
    direct_reads: set[str],
    declared_prefixes: set[str] = frozenset(),
) -> tuple[bool, str]:
    """Return (ok, explanation) for an env var claim."""
    normalized = token.upper()
    if normalized in direct_reads:
        return True, ""
    for prefix in _DYNAMIC_PREFIXES:
        if normalized.startswith(prefix):
            return True, f"dynamic {prefix}namespace"
    for prefix in declared_prefixes:
        if normalized.startswith(prefix):
            return True, f"declared env prefix `{prefix}`"
    if normalized.endswith(_PREFIX_TOKEN_SUFFIX):
        prefix = normalized[: -len(_PREFIX_TOKEN_SUFFIX)]
        matches = [var for var in validity if var.startswith(f"{prefix}__")]
        wildcard_matches = [
            var
            for var in validity
            if "*" in var and _prefix_parts_match(var, prefix)
        ]
        if matches or wildcard_matches:
            count = len(matches) + len(wildcard_matches)
            return True, f"prefix `{prefix}__` maps {count} variables"
        return False, f"no variable starts with prefix `{prefix}__`"
    if "__" not in normalized:
        return False, (
            "not a section/key mapping (`LEX_<SECTION>__<KEY>`), nor read directly"
        )
    section = normalized[4:].split("__", 1)[0]
    if not section:
        return False, "missing section"
    desc = validity.get(normalized)
    if desc is None:
        for valid_key, valid_desc in validity.items():
            if "*" in valid_key and _parts_match(valid_key, normalized):
                desc = f"{valid_desc} (wildcard)"
                break
    if desc is None:
        return False, "no config section/key path matches this variable"
    return True, desc


class DocsClaimsAuditGenerator(MarkdownAuditGenerator):
    """Audit env-var and priority claims in package docs against the framework."""

    name = "docs-claims"
    description = (
        "Generate AUDIT_DOC_CLAIMS.md verifying that every `LEX_*` env var and "
        "`ProviderPriority.*` claim in package docs resolves against the framework."
    )
    output_file = "AUDIT_DOC_CLAIMS.md"

    def run(
        self,
        *,
        root: Path | None = None,
        all_mode: bool = False,
    ) -> AuditRunResult:
        """Execute the claims audit and fail when any claim does not resolve."""
        validation = self.validate(root=root)
        if not validation.success:
            return validation
        resolved_root = self.resolve_root(root)
        output_dir = (
            resolved_root if all_mode else resolved_root / "docs/lexigram-docs/audit"
        )
        output_dir.mkdir(parents=True, exist_ok=True)
        markdown, issue_count = self._render(resolved_root)
        output_path = output_dir / self.output_file
        output_path.write_text(markdown, encoding="utf-8")
        status = "PASS" if issue_count == 0 else f"{issue_count} unresolved claim(s)"
        return AuditRunResult(
            name=self.name,
            success=issue_count == 0,
            message=f"{status} -> wrote {output_path.name}",
            output_path=output_path,
        )

    def render_markdown(self, *, root: Path) -> str:
        """Render the claims audit report (protocol compatibility)."""
        return self._render(root)[0]

    def _render(self, root: Path) -> tuple[str, int]:
        """Build the report body and count unresolved claims."""
        validity = _build_env_validity()
        direct = _build_direct_reads()
        declared = _build_declared_prefixes()
        try:
            priority_mod = importlib.import_module(_PRIORITY_MODULE)
            priority_members = set(getattr(priority_mod, _PRIORITY_ENUM).__members__)
        except Exception:  # noqa: BLE001 - surfaced in the report
            priority_members = set()

        issues: list[ClaimIssue] = []
        verified_vars = 0
        verified_prios = 0
        for package in self.iter_package_roots(root=root):
            docs_dir = package / "docs"
            if not docs_dir.is_dir():
                continue
            for md_file in sorted(docs_dir.glob("*.md")):
                try:
                    text = md_file.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                rel = md_file.relative_to(root).as_posix()
                for token in _collect_env_claims(text):
                    ok, desc = _verify_env_var(token, validity, direct, declared)
                    if ok:
                        if desc:
                            verified_vars += 1
                        continue
                    issues.append(
                        ClaimIssue(doc=rel, claim=token, reason=f"env var: {desc}")
                    )
                for member in _collect_priority_claims(text):
                    if member in priority_members:
                        verified_prios += 1
                        continue
                    issues.append(
                        ClaimIssue(
                            doc=rel,
                            claim=f"ProviderPriority.{member}",
                            reason="no such member on lexigram.contracts.core.provider.ProviderPriority",
                        )
                    )

        lines = [
            "# AUDIT_DOC_CLAIMS.md — Lexigram Documentation Claims Audit",
            "",
            "> **Source**: Every `LEX_*` env var and `ProviderPriority.*` mention in every",
            "> package `docs/*.md` file (prose + python blocks), resolved against the",
            "> installed framework. Env vars must map to a real `*Config` field"
            "> (`LEX_<SECTION>__<KEY>` / `LEX_<PACKAGE>__<KEY>`) or be read directly by",
            "> framework code.",
            "",
            "## Summary",
            "",
            f"- Env vars verified: {verified_vars}",
            f"- Priorities verified: {verified_prios}",
            f"- Unresolved claims: {len(issues)}",
            "",
        ]

        if issues:
            lines.append("## Unresolved Claims")
            lines.append("")
            lines.append("| Doc | Claim | Reason |")
            lines.append("|-----|-------|--------|")
            for issue in sorted(issues, key=lambda i: (i.doc, i.claim)):
                lines.append(f"| `{issue.doc}` | `{issue.claim}` | {issue.reason} |")
            lines.append("")
        else:
            lines.append("No unresolved doc claims detected.")
            lines.append("")

        return "\n".join(lines), len(issues)


__all__ = ["DocsClaimsAuditGenerator"]

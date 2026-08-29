"""Entry point: generate REF_ENV_VARS.md from the scanned config surface."""

from __future__ import annotations

import argparse
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from dev.generators.env_vars_catalog._model import (
    REPO_ROOT,
    YAML_ONLY_FIELDS,
    ConfigClass,
    _md,
)
from dev.generators.env_vars_catalog.env_paths import (
    build_field_paths,
    package_sort_key,
    scan_direct_env_vars,
)
from dev.generators.env_vars_catalog.scan import (
    discover_packages,
    scan_config_classes_in_package,
)


class _Keyed:
    """A config class registered under ``(owner_package, class_name)``."""

    __slots__ = ("cls", "key", "name", "owner")

    def __init__(self, cls: ConfigClass, owner: str) -> None:
        self.cls = cls
        self.owner = owner
        self.name = cls.name
        self.key = (owner, cls.name)


def _build_registry(
    pkg_classes_by_pkg: dict[str, dict[str, ConfigClass]],
) -> dict[tuple[str, str], _Keyed]:
    """Register every scanned class under its own package — no name merging."""
    registry: dict[tuple[str, str], _Keyed] = {}
    for pkg_name, pkg_classes in pkg_classes_by_pkg.items():
        for name, cls in pkg_classes.items():
            registry[(pkg_name, name)] = _Keyed(cls, pkg_name)
    return registry


def _resolve_ref(raw_type: str, registry: dict[tuple[str, str], _Keyed], home: str):
    """Resolve a type annotation to a keyed class, preferring same package."""
    from dev.generators.env_vars_catalog.scan import resolve_config_class

    # Try within the home package first
    home_names = {k[1] for k in registry if k[0] == home}
    probe: dict[str, ConfigClass] = {}
    for k, v in registry.items():
        probe[k[1]] = v.cls  # last wins globally; overridden below per-home

    # Build a resolver view: names unique globally use that class; ambiguous
    # names resolve to the home package's definition when it has one.
    global_by_name: dict[str, int] = {}
    for k in registry:
        global_by_name[k[1]] = global_by_name.get(k[1], 0) + 1
    view: dict[str, ConfigClass] = {}
    view.update({k[1]: v.cls for k, v in registry.items() if global_by_name[k[1]] == 1})
    view.update({k[1]: v.cls for k, v in registry.items() if k[0] == home})
    return resolve_config_class(raw_type, view)


def _select_roots(
    registry: dict[tuple[str, str], _Keyed],
) -> dict[tuple[str, str], _Keyed]:
    """Pick active root configs and suppress child-consumed ones.

    Runtime truth: env vars bind against a root's ``config_section`` namespace.
    A section-carrying class that is reachable as a child config of ANOTHER
    root never loads standalone in practice — it expands under the parent's
    family instead (e.g. ``TTSConfig`` under ``MultimediaConfig``), so its
    standalone family must not be documented.  Same-name collisions across
    packages stay separate entries here, so e.g. core's ``SecurityConfig``
    (section=security) is not suppressed by web's section-less child class of
    the same name.  ``LexigramConfig`` is a root despite having no section
    (its fold validator consumes ``LEX_LEXIGRAM__*``).
    """
    roots = {
        key: entry
        for key, entry in registry.items()
        if entry.cls.config_section or entry.name == "LexigramConfig"
    }

    def _resolve_ref_keys(
        cls: ConfigClass, home: str
    ) -> list[tuple[str, str]]:
        """Registry keys a class's field types resolve to (home package wins)."""
        keys: list[tuple[str, str]] = []
        for field in cls.fields:
            raw = field.type_str.strip().replace('"', "").replace("'", "")
            stripped = raw
            # Mirror resolve_config_class's union splitting
            import re as _re

            for part in _re.split(r"\s*\|\s*", stripped):
                part = part.strip()
                home_key = (home, part)
                if home_key in registry:
                    keys.append(home_key)
                    continue
                owners = [k for k in registry if k[1] == part]
                if len(owners) == 1:
                    keys.append(owners[0])
        return keys

    suppressed: set[tuple[str, str]] = set()
    for key in sorted(roots, key=lambda k: (k[1], k[0])):
        if key in suppressed:
            continue
        stack, seen = [key], {key}
        while stack:
            current = stack.pop()
            current_entry = registry.get(current)
            if current_entry is None:
                continue
            for ref_key in _resolve_ref_keys(current_entry.cls, current_entry.owner):
                if ref_key != current and ref_key in roots:
                    suppressed.add(ref_key)
                if ref_key not in seen:
                    seen.add(ref_key)
                    stack.append(ref_key)
    return {key: entry for key, entry in roots.items() if key not in suppressed}


def _referenced_class_names(
    cls: ConfigClass, home: str, registry: dict[tuple[str, str], _Keyed]
) -> set[str]:
    """Names of known config classes referenced directly by ``cls``'s fields."""
    refs: set[str] = set()
    for field in cls.fields:
        raw = field.type_str.strip().replace('"', "").replace("'", "")
        resolved = _resolve_ref(raw, registry, home)
        if resolved and resolved != cls.name:
            refs.add(resolved)
    return refs


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate REF_ENV_VARS.md")
    parser.add_argument("--all", action="store_true", help="Write generated docs to repo root (publish mode)")
    args = parser.parse_args()

    all_pkg_srcs = discover_packages(include_all=args.all)

    # Register classes per-package so cross-package name collisions
    # (e.g. two different ``SecurityConfig`` classes) stay distinct.
    pkg_classes_by_pkg: dict[str, dict[str, ConfigClass]] = {}
    for pkg_src in all_pkg_srcs:
        pkg_name = pkg_src.parent.name
        pkg_classes_by_pkg[pkg_name] = scan_config_classes_in_package(pkg_src)

    registry = _build_registry(pkg_classes_by_pkg)
    roots = _select_roots(registry)
    print(f"Root config classes ({len(roots)}):")
    for key in sorted(roots, key=lambda k: (k[1], k[0])):
        entry = roots[key]
        print(f"  {key[0]}/{entry.name}: section={entry.cls.config_section}")

    pkg_entries: dict[str, list[dict]] = defaultdict(list)

    for root_key in sorted(roots, key=lambda k: (k[1], k[0])):
        entry = roots[root_key]
        owner_pkg, root_name = entry.owner, entry.name
        section = entry.cls.config_section or "lexigram"
        prefix = f"LEX_{section.upper()}__"

        # Home package's classes shadow same-named classes elsewhere during
        # child resolution.
        merged: dict[str, ConfigClass] = {}
        for k, v in registry.items():
            if k[0] == owner_pkg or sum(1 for kk in registry if kk[1] == k[1]) == 1:
                merged[k[1]] = v.cls
        field_paths = build_field_paths(entry.cls, merged)

        for type_str, field, file_path, dotted in field_paths:
            upper_path = dotted.upper().replace(".", "__")
            env_var = f"{prefix}{upper_path}"
            if env_var in YAML_ONLY_FIELDS:
                continue
            source = f"{Path(file_path).relative_to(REPO_ROOT)}:{root_name}.{dotted}"
            if len(source) > 100:
                source = source[:55] + "..." + source[-40:]

            pkg_entries[owner_pkg].append({
                "env_var": env_var,
                "type": type_str,
                "default": field.default,
                "description": field.description,
                "source": source,
            })

    direct_entries = scan_direct_env_vars()
    for e in direct_entries:
        pkg_entries[e["package"]].append(e)

    total_classes = sum(len(m) for m in pkg_classes_by_pkg.values())
    print(f"\nTotal config classes across all packages: {total_classes}")

    # Deduplicate within each package
    deduped: dict[str, list[dict]] = {}
    for pkg, entries in pkg_entries.items():
        seen: set[str] = set()
        unique: list[dict] = []
        for e in sorted(entries, key=lambda x: x["env_var"]):
            if e["env_var"] not in seen:
                seen.add(e["env_var"])
                unique.append(e)
        deduped[pkg] = unique

    total_unique = sum(len(e) for e in deduped.values())
    print(f"\nTotal unique env vars: {total_unique}")

    # Check for packages not covered
    all_src_pkgs = {s.parent.name for s in discover_packages()}
    covered_pkgs = set(deduped.keys())
    missing = all_src_pkgs - covered_pkgs
    if missing:
        print(f"  Packages with NO env vars: {', '.join(sorted(missing))}")

    lines = _render_markdown(deduped, total_unique, missing)
    refs_dir = REPO_ROOT / "docs/reference" if not args.all else REPO_ROOT
    refs_dir.mkdir(parents=True, exist_ok=True)
    output_path = refs_dir / "REF_ENV_VARS.md"
    output_path.write_text("\n".join(lines) + "\n")
    print(f"\n✅ Generated {output_path}")


def _render_markdown(
    deduped: dict[str, list[dict]], total_unique: int, missing: set[str]
) -> list[str]:
    """Render the REF_ENV_VARS markdown body from deduplicated entries."""
    lines: list[str] = []
    lines.append("# REF_ENV_VARS.md — Lexigram Framework Environment Variables")
    lines.append("")
    lines.append(f"**Date:** {datetime.now(UTC).strftime('%Y-%m-%d')}")
    lines.append(f"**Total entries:** {total_unique}")
    lines.append(f"**Packages:** {len(deduped)}")
    lines.append("")
    lines.append("> Generated by scanning config class fields and tracing nested config hierarchies.")
    lines.append("")
    lines.append("---")

    # Duplicate analysis
    all_vars: dict[str, list[str]] = defaultdict(list)
    for pkg, entries in deduped.items():
        for e in entries:
            all_vars[e["env_var"]].append(pkg)

    dupes = {v: pkgs for v, pkgs in all_vars.items() if len(pkgs) > 1}
    if dupes:
        lines.append("")
        lines.append("## Duplicate Analysis")
        lines.append("")
        lines.append("| Env Var | Occurrences | Packages |")
        lines.append("|---------|-------------|----------|")
        for var in sorted(dupes.keys()):
            pkgs_str = ", ".join(sorted(dupes[var]))
            lines.append(f"| `{var}` | {len(dupes[var])} | {pkgs_str} |")
        lines.append("")
        lines.append("---")
        lines.append("")

    # --- Quality analysis ---
    total_direct = sum(1 for pkg_es in deduped.values() for e in pkg_es if e.get("note"))
    total_empty_desc = sum(1 for pkg_es in deduped.values() for e in pkg_es if not e.get("description"))
    total_complex = sum(1 for pkg_es in deduped.values() for e in pkg_es if "(complex)" in e.get("default", ""))
    if total_direct or total_empty_desc or total_complex or missing:
        lines.append("## Analysis")
        lines.append("")
        if total_direct:
            lines.append(f"- **Direct env access vars**: {total_direct} — accessed via `os.environ.get()` outside config classes")
        if total_empty_desc:
            lines.append(f"- **Missing descriptions**: {total_empty_desc} of {total_unique} ({total_empty_desc * 100 // total_unique}%)")
        if total_complex:
            lines.append(f"- **Complex defaults**: {total_complex} — default values that could not be statically resolved")
        if missing:
            lines.append(f"- **Packages with NO env vars**: {', '.join(sorted(missing))}")
        lines.append("")
        lines.append("---")
        lines.append("")

    lines.append("## Package Registry")
    lines.append("")

    sorted_pkgs = sorted(deduped.keys(), key=package_sort_key)
    for pkg in sorted_pkgs:
        entries = deduped[pkg]
        lines.append(f"### `{pkg}` ({len(entries)} vars)")
        lines.append("")
        lines.append("| Env Var | Type | Default | Description | Source |")
        lines.append("|---------|------|---------|-------------|--------|")
        for e in entries:
            src = e.get("source", "")
            desc = e.get("description", "") or ""
            if len(desc) > 80:
                desc = desc[:77] + "..."
            desc = desc or "—"
            var_type = _md(e["type"])
            default = _md(e["default"])
            desc = _md(desc)
            src = _md(src)
            note = e.get("note", "")
            lines.append(f"| `{e['env_var']}` | {var_type} | {default} | {desc} | `{src}{note}` |")
        lines.append("")

    return lines


if __name__ == "__main__":
    main()

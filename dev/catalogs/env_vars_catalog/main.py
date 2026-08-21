"""Entry point: generate REF_ENV_VARS.md from the scanned config surface."""

from __future__ import annotations

import argparse
import ast
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path

from dev.catalogs.env_vars_catalog._model import (
    CONFIG_BASE_CLASSES,
    REPO_ROOT,
    _md,
)
from dev.catalogs.env_vars_catalog.env_paths import (
    build_field_paths,
    find_env_prefixes,
    package_sort_key,
    scan_direct_env_vars,
)
from dev.catalogs.env_vars_catalog.scan import (
    discover_packages,
    resolve_config_class,
    scan_config_classes_in_package,
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Generate REF_ENV_VARS.md")
    parser.add_argument("--all", action="store_true", help="Write generated docs to repo root (publish mode)")
    args = parser.parse_args()

    all_pkg_srcs = discover_packages(include_all=args.all)
    total_pkg_classes = 0

    env_prefixes = find_env_prefixes()
    print(f"Env prefixes: {len(env_prefixes)}")
    for p, pf in sorted(env_prefixes.items()):
        print(f"  {p}: {pf}")

    pkg_entries: dict[str, list[dict]] = defaultdict(list)

    # Process each package independently to avoid cross-package name collisions
    for pkg_src in all_pkg_srcs:
        pkg_name = pkg_src.parent.name

        # Scan config classes in this package only
        pkg_classes = scan_config_classes_in_package(pkg_src)
        total_pkg_classes += len(pkg_classes)

        if not pkg_classes:
            continue

        # Build within-package child reference map
        within_child: dict[str, bool] = {}
        for name in pkg_classes:
            is_child = False
            for other_name, other_cls in pkg_classes.items():
                if other_name == name:
                    continue
                for f in other_cls.fields:
                    if name in f.type_str.replace('"', "").replace("'", ""):
                        is_child = True
                        break
                if is_child:
                    break
            within_child[name] = is_child

        # Find all files that actually contain Config classes in this package
        config_files = {cls.file_path for cls in pkg_classes.values()}
        for cfg_file in sorted(config_files):
            try:
                text = cfg_file.read_text(encoding="utf-8")
                tree = ast.parse(text, filename=str(cfg_file))
            except (SyntaxError, Exception):
                continue

            for node in ast.walk(tree):
                if not isinstance(node, ast.ClassDef):
                    continue
                if not node.name.endswith("Config"):
                    continue
                if node.name not in pkg_classes:
                    continue

                cls = pkg_classes[node.name]
                used_as_child = within_child.get(node.name, False)
                has_base_config = any(b in CONFIG_BASE_CLASSES for b in cls.bases)

                # BaseConfig subclasses are ALWAYS roots, even if referenced as children
                if used_as_child and not has_base_config:
                    continue

                # Root config must: have BaseConfig base, have empty bases, or have config children
                has_empty_bases = len(cls.bases) == 0
                has_config_children = any(
                    resolve_config_class(f.type_str, pkg_classes) for f in cls.fields
                )

                if not (has_base_config or has_empty_bases or has_config_children):
                    continue

                prefix = env_prefixes.get(pkg_name, f"LEX_{pkg_name.replace('lexigram-', '').upper().replace('-', '_')}__")
                field_paths = build_field_paths(cls, pkg_classes)

                for type_str, field, file_path, dotted in field_paths:
                    upper_path = dotted.upper().replace(".", "__")
                    env_var = f"{prefix}{upper_path}"
                    source = f"{Path(file_path).relative_to(REPO_ROOT)}:{node.name}.{dotted}"
                    if len(source) > 100:
                        source = source[:55] + "..." + source[-40:]

                    pkg_entries[pkg_name].append({
                        "env_var": env_var,
                        "type": type_str,
                        "default": field.default,
                        "description": field.description,
                        "source": source,
                    })

    direct_entries = scan_direct_env_vars()
    for e in direct_entries:
        pkg_entries[e["package"]].append(e)

    print(f"\nTotal config classes across all packages: {total_pkg_classes}")

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

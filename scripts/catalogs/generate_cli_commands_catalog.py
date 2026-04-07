#!/usr/bin/env python3
"""
Generate REF_CLI_COMMANDS.md — authoritative CLI command registry.

Uses the actual CLI output for ground truth, with AST scanning as fallback
for source file metadata.
"""

from __future__ import annotations

import argparse
import ast
import re
import subprocess
import sys
from collections import defaultdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

REPO_ROOT = Path.cwd()


# ── helpers ──────────────────────────────────────────────────────────────

def run_cli(*args: str) -> str:
    """Run `uv run lexigram <args>` and return stdout."""
    cmd = ["uv", "run", "lexigram", *args]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True,
                                timeout=60, cwd=REPO_ROOT)
        return result.stdout
    except subprocess.TimeoutExpired:
        print(f"  ⚠  timeout: uv run lexigram {' '.join(args)}")
        return ""
    except FileNotFoundError:
        print("  ⚠  uv not found")
        return ""


_CMD_RE = re.compile(r"^[a-z][a-z0-9_-]*$")


def _extract_box_content(line: str) -> str | None:
    """Extract content inside a rich box from a line like ``│ content      │``."""
    s = line.strip()
    if not s or s == "│":
        return None
    if not s.startswith("│") or not s.endswith("│"):
        return None
    return s[1:-1].strip()


def parse_typer_help(text: str) -> list[dict[str, str]]:
    """Parse ``lexigram --help`` output into a list of {name, description}."""
    commands: list[dict[str, str]] = []
    in_commands = False
    for line in text.splitlines():
        if "╭─ Commands" in line:
            in_commands = True
            continue
        if "╰" in line and in_commands:
            break
        if not in_commands:
            continue
        content = _extract_box_content(line)
        if content is None:
            continue
        # Split on two or more spaces (Typer uses fixed-width columns)
        parts = re.split(r"  +", content, maxsplit=1)
        if len(parts) == 2:
            candidate = parts[0].strip()
            if _CMD_RE.match(candidate):
                commands.append({"name": candidate, "description": parts[1].strip()})
            elif commands:
                # Leading spaces before description — continuation line
                commands[-1]["description"] += " " + content.strip()
        elif commands and len(parts) == 1:
            # No split at all — the entire content is description continuation
            commands[-1]["description"] += " " + content.strip()
    return commands


# ── contributor discovery via pyproject.toml ────────────────────────────

def scan_contributor_entry_points() -> list[dict[str, str]]:
    """Read lexigram.cli.contributors from all pyproject.toml files."""
    groups: list[dict[str, str]] = []
    for tf in REPO_ROOT.glob("lexigram-*/pyproject.toml"):
        pkg = tf.parent.name
        try:
            text = tf.read_text(encoding="utf-8")
        except Exception:
            continue
        for m in re.finditer(
            r'\[project\.entry-points\.("?)lexigram\.cli\.contributors\1\]\s*(.+?)(?=\n\[|\Z)',
            text, re.DOTALL
        ):
            block = m.group(2)
            for entry in re.finditer(r'(\w+)\s*=\s*"(.+?)"', block):
                groups.append({
                    "name": entry.group(1),
                    "package": pkg,
                    "target": entry.group(2),
                })
    return sorted(groups, key=lambda x: x["name"])


# ── source file scanner (used for the Source Files table) ────────────────

def extract_typer_commands(file_path: Path) -> list[dict]:
    """Extract Typer subcommand names from a .py file via AST."""
    try:
        text = file_path.read_text(encoding="utf-8")
        tree = ast.parse(text, filename=str(file_path))
    except (SyntaxError, Exception):
        return []

    commands: list[str] = []
    typer_vars: set[str] = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and isinstance(node.value, ast.Call):
                    fn = ast.unparse(node.value.func)
                    if "Typer" in fn:
                        typer_vars.add(target.id)

    for node in ast.walk(tree):
        if not isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            continue
        for decorator in node.decorator_list:
            fn = None
            if isinstance(decorator, ast.Call):
                fn = ast.unparse(decorator.func)
            elif isinstance(decorator, ast.Attribute):
                fn = ast.unparse(decorator)

            if fn and "." in fn:
                app_var, method = fn.split(".", 1)
                if app_var in typer_vars and method.startswith("command"):
                    cmd_name = node.name
                    if isinstance(decorator, ast.Call) and decorator.args:
                        if isinstance(decorator.args[0], ast.Constant):
                            cmd_name = decorator.args[0].value
                    commands.append(cmd_name)

    return [{"name": c} for c in commands]


# ── main ─────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Generate REF_CLI_COMMANDS.md")
    parser.add_argument("--all", action="store_true", help="Output to repo root instead of docs")
    args = parser.parse_args()

    print("Scanning CLI commands…")

    contributed_groups = scan_contributor_entry_points()
    print(f"  Contributed groups: {len(contributed_groups)}")

    # ── Run the actual CLI to discover commands ──
    help_text = run_cli("--help")
    top_commands = parse_typer_help(help_text)
    print(f"  Top-level commands: {len(top_commands)}")

    # Separate built-in from contributed at the top level by matching
    # names we see in help vs what entry points register.
    contributed_names = {g["name"] for g in contributed_groups}
    builtin_names = {c["name"] for c in top_commands} - contributed_names
    contributed_top = [c for c in top_commands if c["name"] in contributed_names]
    builtin_top = [c for c in top_commands if c["name"] not in contributed_names]

    # ── Drill into each builtin group for subcommands ──
    builtin_sub: dict[str, list[dict]] = {}
    for cmd in builtin_top:
        detail = run_cli(cmd["name"], "--help")
        sub = parse_typer_help(detail)
        builtin_sub[cmd["name"]] = sub

    # ── Generators from `lexigram gen` ──
    gen_help = run_cli("gen", "--help")
    generators = parse_typer_help(gen_help)
    # Remove the built-in "list" from generators list
    gen_commands = [g for g in generators if g["name"] != "list"]
    print(f"  Generators: {len(gen_commands)}")

    # ── Source files table via AST ──
    src_entries: list[tuple[str, str, str]] = []

    # lexigram-cli commands/
    cli_cmds_dir = REPO_ROOT / "lexigram-cli" / "src" / "lexigram" / "cli" / "commands"
    if cli_cmds_dir.exists():
        for pyfile in sorted(cli_cmds_dir.glob("*.py")):
            if pyfile.name == "__init__.py":
                continue
            cmds = extract_typer_commands(pyfile)
            names = [c["name"] for c in cmds]
            if names:
                rel = pyfile.relative_to(REPO_ROOT)
                src_entries.append(("lexigram-cli", str(rel), ", ".join(names[:6])))

    # main.py
    main_py = REPO_ROOT / "lexigram-cli" / "src" / "lexigram" / "cli" / "runtime" / "main.py"
    if main_py.exists():
        rel = main_py.relative_to(REPO_ROOT)
        src_entries.append(("lexigram-cli", str(rel), "entry point, command registration"))

    # Extension cli/commands.py
    for cg in contributed_groups:
        pkg = cg["package"]
        inner = pkg.replace("lexigram-", "lexigram/", 1).replace("-", "/")
        cmds_file = REPO_ROOT / pkg / "src" / inner / "cli" / "commands.py"
        if cmds_file.exists():
            cmds = extract_typer_commands(cmds_file)
            names = [c["name"] for c in cmds]
            if names:
                rel = cmds_file.relative_to(REPO_ROOT)
                src_entries.append((pkg, str(rel), ", ".join(names[:6])))

    total_packages = len({s[0] for s in src_entries} | {g["package"] for g in contributed_groups})

    # ── Build markdown ──
    lines: list[str] = []
    lines.append("# REF_CLI_COMMANDS.md — Lexigram CLI Command Registry")
    lines.append("")
    lines.append(f"**Date:** {datetime.now(UTC).strftime('%Y-%m-%d')}")
    lines.append(f"**Total entries:** {len(top_commands) + len(gen_commands)}")
    lines.append(f"**Packages:** {total_packages}")
    lines.append("")
    lines.append("> Auto-generated by running the actual CLI and scanning pyproject.toml entry points.")
    lines.append("")

    # ── Command Tree ──
    lines.append("## Command Tree")
    lines.append("")
    lines.append("```")
    lines.append("lexigram")
    for cmd in builtin_top:
        n = cmd["name"]
        d = cmd["description"]
        sub = builtin_sub.get(n, [])
        if sub:
            lines.append(f"├── {n:<16} {d}")
            for s in sub:
                lines.append(f"│   └── {s['name']:<14} {s['description']}")
            lines.append("│")
        else:
            lines.append(f"├── {n:<16} {d}")
    if contributed_top:
        lines.append("│")
        lines.append("│   [Contributed via entry points]")
        for cmd in contributed_top:
            lines.append(f"├── {cmd['name']:<16} {cmd['description']}")
    lines.append("```")
    lines.append("")

    # ── Generator Inventory ──
    lines.append("## Generator Inventory")
    lines.append("")
    lines.append(f"**Total: {len(gen_commands)} generators**")
    lines.append("")
    lines.append("| Generator | Description |")
    lines.append("|-----------|-------------|")
    for g in gen_commands:
        lines.append(f"| `lexigram gen {g['name']}` | {g['description']} |")
    lines.append("")

    # ── Contributed Command Groups ──
    lines.append("---")
    lines.append("")
    lines.append("## Contributed Command Groups")
    lines.append("")
    lines.append("These command groups are registered via the `lexigram.cli.contributors`")
    lines.append("entry-point and loaded at runtime by the CLI's contributor discovery system.")
    lines.append("")
    lines.append(f"**{len(contributed_groups)} groups across {len({g['package'] for g in contributed_groups})} packages**")
    lines.append("")
    lines.append("| Group | Package | Target |")
    lines.append("|-------|---------|--------|")
    for cg in contributed_groups:
        lines.append(f"| `lexigram {cg['name']}` | {cg['package']} | `{cg['target']}` |")
    lines.append("")

    # ── Source Files ──
    lines.append("---")
    lines.append("")
    lines.append("## Source Files")
    lines.append("")
    lines.append("| Package | File | Commands |")
    lines.append("|---------|------|----------|")
    for pkg, path, desc in src_entries:
        lines.append(f"| {pkg} | `{path}` | {desc} |")
    lines.append("")

    refs_dir = REPO_ROOT / "docs/lexigram-docs/reference" if not args.all else REPO_ROOT
    refs_dir.mkdir(parents=True, exist_ok=True)
    output_path = refs_dir / "REF_CLI_COMMANDS.md"
    output_path.write_text("\n".join(lines) + "\n")
    print(f"\n✅ Generated {output_path}")
    print(f"   {len(top_commands)} top-level commands ({len(builtin_top)} built-in + {len(contributed_top)} contributed)")
    print(f"   {len(gen_commands)} generators")
    print(f"   {len(contributed_groups)} contributed groups")
    print(f"   {total_packages} packages")


if __name__ == "__main__":
    main()

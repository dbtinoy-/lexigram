from __future__ import annotations

from importlib.metadata import entry_points

from lexigram.cli.contributors.runtime import ENTRY_POINT_GROUP

_NON_SCOPE_WITH_ENTRY_POINT = {
    "admin",  # lexigram-admin — experimental tier, documented as non-scope
}


def _check_implements_protocol(obj: object) -> bool:
    return hasattr(obj, "contributor_id") and hasattr(obj, "get_generators")


def test_all_entry_points_load_successfully() -> None:
    eps = list(entry_points(group=ENTRY_POINT_GROUP))
    assert eps, "Expected at least the core CLI contributor"

    for ep in eps:
        cls = ep.load()
        instance = cls()
        assert _check_implements_protocol(instance), (
            f"{ep.name} does not satisfy CliContributorProtocol"
        )


def test_published_package_list_matches_cli_matrix(repo_root: Path) -> None:
    import re

    publish_script = repo_root / "tools" / "publish_public.sh"
    assert publish_script.is_file(), f"publish_public.sh not found at {publish_script}"
    text = publish_script.read_text()

    match = re.search(r'STABLE_PKGS="(.*?)"', text, re.DOTALL)
    assert match, "STABLE_PKGS not found in publish_public.sh"
    publish_pkgs = {p.strip() for p in match.group(1).split() if p.strip() and p.strip() != "\\"}

    matrix_doc = repo_root / "lexigram-cli" / "docs" / "PUBLIC_PACKAGE_CLI_MATRIX.md"
    assert matrix_doc.is_file(), f"Matrix doc not found at {matrix_doc}"
    matrix_text = matrix_doc.read_text()

    missing = []
    for pkg in sorted(publish_pkgs):
        if f"`{pkg}`" not in matrix_text:
            missing.append(pkg)
    assert not missing, (
        f"Packages in publish_public.sh missing from PUBLIC_PACKAGE_CLI_MATRIX.md: "
        f"{', '.join(missing)}"
    )

    actual_eps = {ep.name for ep in entry_points(group=ENTRY_POINT_GROUP)}
    matrix_subset = set()
    for pkg in publish_pkgs:
        ep_key = pkg.replace("lexigram-", "", 1) if pkg.startswith("lexigram-") else pkg
        if ep_key == "lexigram":
            ep_key = "core"
        matrix_subset.add(ep_key)

    matrix_in_actual = matrix_subset & actual_eps
    assert matrix_in_actual, (
        f"No published packages match actual entry points. "
        f"Matrix: {matrix_subset}, Actual: {actual_eps}"
    )


def test_cli_runtime_does_not_import_extension_packages_directly() -> None:
    import ast
    from pathlib import Path

    cli_src = Path(__file__).parent.parent.parent / "src" / "lexigram" / "cli"
    forbidden_prefixes = {
        "lexigram.web",
        "lexigram.sql",
        "lexigram.auth",
        "lexigram.events",
        "lexigram.cache",
        "lexigram.ai",
    }

    py_files = list(cli_src.rglob("*.py"))
    assert py_files, f"No Python files found in {cli_src}"

    for py_file in py_files:
        if "templates" in str(py_file):
            continue
        source = py_file.read_text()
        if "from __future__" not in source:
            continue
        tree = ast.parse(source)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    for forbidden in forbidden_prefixes:
                        assert not alias.name.startswith(forbidden), (
                            f"{py_file} imports {alias.name} (forbidden extension import)"
                        )
            elif isinstance(node, ast.ImportFrom):
                if node.module and any(
                    node.module.startswith(f) for f in forbidden_prefixes
                ):
                    raise AssertionError(
                        f"{py_file} imports from {node.module} (forbidden extension import)"
                    )


def test_all_active_contributors_provide_contributor_id() -> None:
    runtime = _load_runtime()
    for contributor in runtime.contributors:
        assert contributor.contributor_id, (
            "Contributor must provide non-empty contributor_id"
        )


def _load_runtime():
    from lexigram.cli.contributors.runtime import ContributorRuntime

    return ContributorRuntime.from_entry_points()


def test_deploy_not_in_command_registry() -> None:
    from lexigram.cli.runtime.main import _BUILTIN_COMMANDS

    assert "deploy" not in _BUILTIN_COMMANDS

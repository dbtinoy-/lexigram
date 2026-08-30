"""Code preview emitter — produces preview output for the frontend code tab.

``emit_code_preview`` generates a preview of the files that would be
created by ``write_project``.  The frontend code tab renders this output,
so it must match ``generate`` exactly.
"""

from __future__ import annotations

from dataclasses import dataclass

from lexigram_builder.gen.emitters.scaffold import emit_scaffold_files
from lexigram_builder.graph.models import (
    AuthConfig,
    ContractConfig,
    FeatureFlagConfig,
    RateLimitConfig,
    RoleConfig,
)


@dataclass(frozen=True, slots=True)
class PreviewFile:
    """A single file in the code preview.

    Attributes:
        path: Relative path inside the generated project.
        content: File content.
        language: Language hint for syntax highlighting.
    """

    path: str
    content: str
    language: str = "python"


@dataclass(frozen=True, slots=True)
class CodePreview:
    """Full code preview result.

    Attributes:
        files: List of preview files.
    """

    files: tuple[PreviewFile, ...]


def _preview_feature_flag(name: str, description: str) -> PreviewFile:
    """Generate a preview for a feature flag definition."""
    pascal = "".join(word.capitalize() for word in name.split("_"))
    content = (
        f'"""{pascal} feature flag.\n'
        f"\n"
        f"Generated scaffold — declare the flag key and default rollout here so\n"
        f"the rest of the application imports one canonical definition.\n"
        f'"""\n'
        f"\n"
        f"from __future__ import annotations\n"
        f"\n"
        f"from dataclasses import dataclass\n"
        f"\n"
        f"\n"
        f"@dataclass(frozen=True, slots=True)\n"
        f"class {pascal}Flag:\n"
        f'    """Definition of the ``{name}`` feature flag."""\n'
        f"\n"
        f'    key = "{name}"\n'
        f'    description = "Toggle for the {pascal} feature"\n'
        f"    default_enabled = False\n"
        f"\n"
        f"    @classmethod\n"
        f"    def is_enabled(cls, context: dict[str, object] | None = None) -> bool:\n"
        f'        """Return whether the flag is enabled for *context*."""\n'
        f"        return cls.default_enabled\n"
    )
    return PreviewFile(
        path=f"src/app/features/{name}_flag.py",
        content=content,
    )


def _preview_auth_guard(name: str) -> PreviewFile:
    """Generate a preview for an auth guard definition."""
    pascal = "".join(word.capitalize() for word in name.split("_"))
    content = (
        f'"""{pascal} authentication guard.\n'
        f"\n"
        f"Generated scaffold — configure authentication requirements here.\n"
        f'"""\n'
        f"\n"
        f"from __future__ import annotations\n"
        f"\n"
        f"from lexigram.auth.authz.guards import require_auth\n"
        f"\n"
        f"\n"
        f"def {name}_guard() -> None:\n"
        f'    """Apply {pascal} authentication guard.\n'
        f"\n"
        f"    Use as a decorator on route handlers:\n"
        f"\n"
        f"        @{name}_guard()\n"
        f"        async def protected_endpoint(request):\n"
        f"            ...\n"
        f'    """\n'
        f"    return require_auth()\n"
    )
    return PreviewFile(
        path=f"src/app/guards/{name}_auth_guard.py",
        content=content,
    )


def _preview_role_guard(name: str, permissions: tuple[str, ...]) -> PreviewFile:
    """Generate a preview for a role guard definition."""
    pascal = "".join(word.capitalize() for word in name.split("_"))
    perms_str = ", ".join(f'"{p}"' for p in permissions) if permissions else ""
    content = (
        f'"""{pascal} role guard.\n'
        f"\n"
        f"Generated scaffold — define role requirements here.\n"
        f'"""\n'
        f"\n"
        f"from __future__ import annotations\n"
        f"\n"
        f"from lexigram.auth.authz.guards import require_roles\n"
        f"\n"
        f"\n"
        f"def {name}_guard() -> None:\n"
        f'    """Apply {pascal} role guard.\n'
        f"\n"
        f"    Use as a decorator on route handlers:\n"
        f"\n"
        f"        @{name}_guard()\n"
        f"        async def admin_endpoint(request):\n"
        f"            ...\n"
        f'    """\n'
        f"    return require_roles({perms_str})\n"
    )
    return PreviewFile(
        path=f"src/app/guards/{name}_guard.py",
        content=content,
    )


def _preview_rate_limit(name: str, strategy: str, max_requests: int, window_seconds: int) -> PreviewFile:
    """Generate a preview for a rate-limit definition."""
    pascal = "".join(word.capitalize() for word in name.split("_"))
    content = (
        f'"""Rate limit definition: {name}.\n'
        f"\n"
        f"Generated scaffold — configure rate limiting parameters here.\n"
        f'"""\n'
        f"\n"
        f"from __future__ import annotations\n"
        f"\n"
        f"from dataclasses import dataclass\n"
        f"\n"
        f"\n"
        f"@dataclass(frozen=True, slots=True)\n"
        f"class {pascal}RateLimit:\n"
        f'    """Rate limit configuration for {name}."""\n'
        f"\n"
        f'    strategy = "{strategy}"\n'
        f"    max_requests = {max_requests}\n"
        f"    window_seconds = {window_seconds}\n"
    )
    return PreviewFile(
        path=f"src/app/guards/{name}_rate_limit.py",
        content=content,
    )


def _preview_contract(name: str, direction: str, fields: str) -> PreviewFile:
    """Generate a preview for a contract/DTO definition."""
    pascal = "".join(word.capitalize() for word in name.split("_"))
    # Parse fields into Pydantic-style field declarations
    field_lines: list[str] = []
    for part in fields.split(","):
        part = part.strip()
        if not part or ":" not in part:
            continue
        fname, ftype = part.split(":", 1)
        fname = fname.strip()
        ftype = ftype.strip().rstrip("?")
        # Map to Python types
        type_map = {
            "str": "str",
            "int": "int",
            "float": "float",
            "bool": "bool",
            "datetime": "datetime",
            "date": "date",
            "uuid": "str",
            "decimal": "float",
            "text": "str",
            "json": "dict",
            "list": "list",
            "dict": "dict",
        }
        py_type = type_map.get(ftype, "str")
        required = "?" not in part
        if required:
            field_lines.append(f"    {fname}: {py_type}")
        else:
            field_lines.append(f"    {fname}: {py_type} | None = None")

    fields_block = "\n".join(field_lines) if field_lines else "    pass"

    content = (
        f'"""{pascal} contract.\n'
        f"\n"
        f"Generated scaffold — define request/response schemas here.\n"
        f'"""\n'
        f"\n"
        f"from __future__ import annotations\n"
        f"\n"
        f"from pydantic import BaseModel\n"
        f"\n"
        f"\n"
    )

    if direction in ("request", "both"):
        content += (
            f"class {pascal}Request(BaseModel):\n"
            f'    """Request schema for {name}."""\n'
            f"\n"
            f"{fields_block}\n"
            f"\n"
            f"\n"
        )

    if direction in ("response", "both"):
        content += (
            f"class {pascal}Response(BaseModel):\n"
            f'    """Response schema for {name}."""\n'
            f"\n"
            f"{fields_block}\n"
        )

    return PreviewFile(
        path=f"src/app/contracts/{name}.py",
        content=content,
    )


def emit_code_preview(
    *,
    project_name: str = "app",
    features: tuple[FeatureFlagConfig, ...] = (),
    auth_configs: tuple[AuthConfig, ...] = (),
    role_configs: tuple[RoleConfig, ...] = (),
    rate_limit_configs: tuple[RateLimitConfig, ...] = (),
    contract_configs: tuple[ContractConfig, ...] = (),
    guard_routes: dict[str, list[str]] | None = None,
) -> CodePreview:
    """Emit a code preview for the frontend code tab.

    Args:
        project_name: The project's snake_case name.
        features: Collected feature flag configs.
        auth_configs: Collected auth configs.
        role_configs: Collected role configs.
        rate_limit_configs: Collected rate-limit configs.
        contract_configs: Collected contract configs.
        guard_routes: Mapping of route path → list of guard decorator names.

    Returns:
        A :class:`CodePreview` with the preview files.
    """
    files: list[PreviewFile] = []

    # Feature flags
    for flag in features:
        files.append(_preview_feature_flag(flag.name, flag.description))

    # Auth guards
    for auth in auth_configs:
        files.append(_preview_auth_guard(auth.name))

    # Role guards
    for role in role_configs:
        files.append(_preview_role_guard(role.name, role.permissions))

    # Rate limits
    for rl in rate_limit_configs:
        files.append(
            _preview_rate_limit(rl.name, rl.strategy, rl.max_requests, rl.window_seconds)
        )

    # Contracts
    for contract in contract_configs:
        files.append(_preview_contract(contract.name, contract.direction, contract.fields))

    # Scaffold files
    scaffold = emit_scaffold_files(
        project_name=project_name,
        features=features,
        auth_configs=auth_configs,
        role_configs=role_configs,
        rate_limit_configs=rate_limit_configs,
        contract_configs=contract_configs,
        guard_routes=guard_routes,
    )
    files.append(PreviewFile(path="main.py", content=scaffold.main_py))
    files.append(PreviewFile(path="di_provider.py", content=scaffold.di_provider))
    for module_name, module_content in scaffold.modules:
        files.append(PreviewFile(path=f"src/app/guards/{module_name}", content=module_content))

    return CodePreview(files=tuple(files))


__all__ = ["CodePreview", "PreviewFile", "emit_code_preview"]

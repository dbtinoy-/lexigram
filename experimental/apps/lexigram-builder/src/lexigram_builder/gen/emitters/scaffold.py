"""Scaffold emitter — generates app-level wiring (main.py, DI, module registration).

``emit_scaffold_files`` produces the top-level ``main.py``, the DI
provider, and module registration code for a generated project.  It
consumes the collected node configs and emits the appropriate imports
and module registrations.
"""

from __future__ import annotations

from dataclasses import dataclass

from lexigram_builder.graph.models import (
    AuthConfig,
    ContractConfig,
    FeatureFlagConfig,
    RateLimitConfig,
    RoleConfig,
    RouteConfig,
)


@dataclass(frozen=True, slots=True)
class ScaffoldResult:
    """Result of scaffold emission.

    Attributes:
        main_py: Content for ``main.py``.
        di_provider: Content for the DI provider module.
        modules: List of ``(module_name, content)`` tuples for additional modules.
    """

    main_py: str
    di_provider: str
    modules: tuple[tuple[str, str], ...] = ()


def emit_scaffold_files(
    *,
    project_name: str = "app",
    routes: tuple[RouteConfig, ...] = (),
    features: tuple[FeatureFlagConfig, ...] = (),
    auth_configs: tuple[AuthConfig, ...] = (),
    role_configs: tuple[RoleConfig, ...] = (),
    rate_limit_configs: tuple[RateLimitConfig, ...] = (),
    contract_configs: tuple[ContractConfig, ...] = (),
    guard_routes: dict[str, list[str]] | None = None,
) -> ScaffoldResult:
    """Emit scaffold files for a generated project.

    Args:
        project_name: The project's snake_case name.
        routes: Collected route configs.
        features: Collected feature flag configs.
        auth_configs: Collected auth configs.
        role_configs: Collected role configs.
        rate_limit_configs: Collected rate-limit configs.
        contract_configs: Collected contract configs.
        guard_routes: Mapping of route path → list of guard decorator names.

    Returns:
        A :class:`ScaffoldResult` with the generated file contents.
    """
    imports: list[str] = []
    registrations: list[str] = []
    provider_imports: list[str] = []
    provider_bodies: list[str] = []

    # ── Feature flags ─────────────────────────────────────────────────
    if features:
        imports.append("from lexigram.features import FeatureFlagsModule")
        imports.append("from lexigram.features.config import FeatureFlagsConfig")
        flag_names = [f'"{f.name}"' for f in features]
        registrations.append(
            f"    FeatureFlagsModule.configure(\n"
            f"        FeatureFlagsConfig(initial_flags={{name: True for name in [{', '.join(flag_names)}]}})\n"
            f"    ),"
        )

    # ── Auth / guards ─────────────────────────────────────────────────
    if auth_configs or role_configs:
        imports.append("from lexigram.auth.authz.guards import require_auth, require_roles")

    # ── Rate limiting ─────────────────────────────────────────────────
    if rate_limit_configs:
        imports.append("from lexigram.auth.web.middleware.throttle import RateLimitMiddleware")

    # ── Contracts ─────────────────────────────────────────────────────
    for contract in contract_configs:
        imports.append(f"from app.contracts.{contract.name} import {contract.name}")

    # ── Build main.py ─────────────────────────────────────────────────
    main_lines: list[str] = [
        '"""Generated application entry point."""',
        "",
        "from __future__ import annotations",
        "",
        "from lexigram.di.module import module, Module",
    ]

    if imports:
        main_lines.append("")
        main_lines.extend(sorted(set(imports)))

    main_lines.extend(
        [
            "",
            "",
            "@module(",
            "    imports=[",
        ]
    )

    if registrations:
        main_lines.extend(registrations)
    else:
        main_lines.append("        # No modules registered")

    main_lines.extend(
        [
            "    ]",
            ")",
            "class AppModule(Module):",
            '    """Root application module."""',
            "    pass",
            "",
        ]
    )

    main_py = "\n".join(main_lines)

    # ── Build DI provider ─────────────────────────────────────────────
    di_lines: list[str] = [
        '"""Generated DI provider."""',
        "",
        "from __future__ import annotations",
        "",
    ]

    if provider_imports:
        di_lines.extend(sorted(set(provider_imports)))
        di_lines.append("")

    di_lines.extend(
        [
            "",
            "# DI provider registrations are handled by the module system.",
            "# Add custom provider bindings here as needed.",
            "",
        ]
    )

    di_provider = "\n".join(di_lines)

    # ── Additional modules ────────────────────────────────────────────
    modules: list[tuple[str, str]] = []

    # Rate-limit definition module
    for rl in rate_limit_configs:
        rl_content = (
            f'"""Rate limit definition: {rl.name}."""\n'
            f"\n"
            f"from __future__ import annotations\n"
            f"\n"
            f"from dataclasses import dataclass\n"
            f"\n"
            f"\n"
            f"@dataclass(frozen=True, slots=True)\n"
            f"class {rl.name}:\n"
            f'    """Rate limit configuration for {rl.name}."""\n'
            f"\n"
            f'    strategy = "{rl.strategy}"\n'
            f"    max_requests = {rl.max_requests}\n"
            f"    window_seconds = {rl.window_seconds}\n"
            f"\n"
        )
        modules.append((f"{rl.name}_rate_limit.py", rl_content))

    return ScaffoldResult(
        main_py=main_py,
        di_provider=di_provider,
        modules=tuple(modules),
    )


__all__ = ["ScaffoldResult", "emit_scaffold_files"]

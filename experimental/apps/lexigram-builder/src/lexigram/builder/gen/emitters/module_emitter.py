"""Module boundary emitter (modular codegen G1, G2).

One Module node becomes a bounded context: a package under
``src/<app>/modules/<slug>/`` holding the ``@module`` boundary, its public
protocols and its DI provider. A second, merged file --
``modules/__init__.py`` -- registers every module so the composition root
picks them up.

**The empty case is upstream's bytes, not a copy of them.** An empty Module
node must produce exactly what ``lexigram new module <slug>`` produces,
because the day the two disagree is the day a canvas-built project stops
being a normal Lexigram project. A test comparing our templates against the
CLI's would catch that a day late; instead this module *calls* the CLI's
scaffold and enriches the result only where the node asks for more than the
bare scaffold. Drift is then impossible for the baseline, and the gate test
only has to prove the enrichment is additive.

That means importing a private helper (``_module_scaffold_files``). It is a
deliberate trade: a private import fails loudly at import time if upstream
renames it, whereas a duplicated template fails silently and much later. If
it is ever made public, drop the underscore and nothing else changes.
"""

from __future__ import annotations

import re

from lexigram.builder.graph.models import ModuleConfig
from lexigram.cli.scaffold import (  # noqa: PLC2701 -- see module docstring
    _module_scaffold_files,
    _modules_init,
)

_MODULE_DIR = "modules"


def module_class_name(slug: str) -> str:
    """``billing_ops`` -> ``BillingOpsModule`` (the CLI's own rule)."""
    return "".join(part.capitalize() for part in re.split(r"[-_]", slug)) + "Module"


def module_title(slug: str) -> str:
    """``billing_ops`` -> ``Billing Ops``, as the CLI titles its docstrings."""
    return module_class_name(slug).removesuffix("Module").replace("_", " ").title()


def provider_class_name(slug: str) -> str:
    return module_title(slug).replace(" ", "") + "Provider"


def _is_bare(config: ModuleConfig) -> bool:
    """True when the node asks for exactly the CLI's scaffold.

    Compared against the dataclass defaults rather than a hand-written list
    of conditions, so a new field added to ``ModuleConfig`` cannot silently
    fall outside this check -- if it has a default and is left alone the
    module is still bare, and if it is set the enriched path runs.
    """
    default = ModuleConfig(name=config.name)
    return config == default


def emit_module_package(
    config: ModuleConfig,
    *,
    app_package: str,
    imports: tuple[str, ...] = (),
    register_provider: bool = False,
    framework_imports: tuple[tuple[str, str], ...] = (),
) -> dict[str, str]:
    """Return ``{relative path: content}`` for one bounded context.

    Args:
        config: The Module node's config.
        app_package: The generated app's python package name.
        imports: Slugs this module imports, derived from cross-module edges
            (never stored on the config -- taxonomy rule M2).
        framework_imports: ``(import line, class name)`` pairs for framework
            DI modules this bounded context must import -- e.g.
            ``DatabaseModule`` when its provider resolves the database. The
            caller supplies them rather than this module deriving them, so
            the package layout stays known in exactly one place.
        register_provider: Declare the module's provider in its metadata.
            Off by default because the CLI's scaffold provider is empty and
            registering it would break byte-parity for a bare module; the
            writer turns it on as soon as the provider actually binds
            something (see G9 in ``03-MODULAR_CODEGEN.md``).

    Returns:
        A mapping of repo-relative paths to file contents.
    """
    slug = config.name
    class_name = module_class_name(slug)
    files = dict(_module_scaffold_files(app_package, slug, class_name))

    if _is_bare(config) and not imports and not register_provider:
        return files

    base = f"src/{app_package}/{_MODULE_DIR}/{slug}"
    files[f"{base}/__init__.py"] = _boundary(
        config,
        app_package=app_package,
        imports=imports,
        register_provider=register_provider,
        framework_imports=framework_imports,
    )

    if config.protocols:
        if config.exports:
            files[f"{base}/protocols.py"] = _protocols(config)
    else:
        # `lexigram new module` always writes protocols.py, so removing it is
        # an explicit choice the node has to make; the boundary stays legal
        # without it, it just has nothing public to say.
        files.pop(f"{base}/protocols.py", None)

    if config.provider:
        if config.health or config.provider_priority != "DOMAIN" or config.exports:
            files[f"{base}/provider.py"] = _provider(config)
    else:
        files.pop(f"{base}/provider.py", None)

    return files


def emit_modules_registry(slugs: tuple[str, ...], *, app_package: str) -> str:
    """Return the merged ``modules/__init__.py``.

    One file for all modules, rewritten wholesale and sorted by slug -- the
    CLI's ``_register_module_in_init`` sorts too, so regeneration and
    ``lexigram new module`` converge on the same bytes instead of racing to
    append.
    """
    names = tuple(sorted((slug, module_class_name(slug)) for slug in set(slugs)))
    return _modules_init(app_package, names)


# ── enriched renderers ───────────────────────────────────────────────────


def _boundary(
    config: ModuleConfig,
    *,
    app_package: str,
    imports: tuple[str, ...],
    register_provider: bool = False,
    framework_imports: tuple[tuple[str, str], ...] = (),
) -> str:
    slug = config.name
    class_name = module_class_name(slug)
    title = module_title(slug)
    summary = config.description.strip() or f"{title} module."
    if not summary.endswith("."):
        summary += "."

    decorator_args: list[str] = []
    if config.is_global:
        decorator_args.append("is_global=True")
    decorator = f"@module({', '.join(decorator_args)})"

    exports = tuple(dict.fromkeys(e.protocol for e in config.exports))
    declare_exports = bool(exports) and config.protocols

    lines = [
        f"from {app_package}.{_MODULE_DIR}.{other} import {module_class_name(other)}"
        for other in sorted(set(imports))
    ]
    lines.extend(line for line, _cls in framework_imports)
    if register_provider:
        lines.append(
            f"from {app_package}.{_MODULE_DIR}.{slug}.provider "
            f"import {provider_class_name(slug)}"
        )
    if declare_exports:
        joined = ", ".join(exports)
        lines.append(
            f"from {app_package}.{_MODULE_DIR}.{slug}.protocols import {joined}"
        )
    import_lines = "\n".join(sorted(lines))
    local_imports = f"\n{import_lines}\n" if import_lines else ""

    # Metadata is declared as class attributes rather than passed to
    # ``@module(...)``: the decorator reads ClassVar defaults off the
    # ``Module`` base (usage pattern 1 in its own docstring), the framework's
    # own fixtures are written this way, and it keeps each list next to the
    # docstring that explains the boundary.
    #
    # It has to be *static* metadata rather than a ``configure()`` factory,
    # because ``modules/__init__.py`` registers bare classes -- the compiler
    # only calls ``configure()`` on a descriptor someone already invoked, so
    # a generated ``configure()`` would be dead code. See G9.
    body = f'    """{summary}"""\n'
    # A module's provider can only resolve what its module imports: the
    # container enforces visibility, so a bounded context that binds
    # repositories has to import DatabaseModule or its provider raises
    # ModuleVisibilityError at boot -- after migrations have already run.
    imported = sorted({module_class_name(o) for o in imports}) + sorted(
        {cls for _line, cls in framework_imports}
    )
    if imported:
        entries = "".join(f"        {name},\n" for name in imported)
        body += f"\n    imports = [\n{entries}    ]\n"
    if register_provider:
        body += f"\n    providers = [{provider_class_name(slug)}]\n"
    if declare_exports:
        entries = "".join(f"        {name},\n" for name in exports)
        body += f"\n    exports = [\n{entries}    ]\n"

    return f'''"""{slug} module - bounded context.

``lexigram gen <component> <name> --module {slug}`` writes module-local
components (controllers, models, services, repositories, ...) into this
package; ``lexigram gen`` without ``--module`` writes cross-cutting
components into the shared layer.
"""

from __future__ import annotations

from lexigram.di.module import Module, module
{local_imports}

{decorator}
class {class_name}(Module):
{body}'''


def _protocols(config: ModuleConfig) -> str:
    slug = config.name
    blocks: list[str] = []
    for export in config.exports:
        doc = export.description.strip() or f"Contract exposed by the {slug} module."
        if not doc.endswith("."):
            doc += "."
        blocks.append(
            f'@runtime_checkable\nclass {export.protocol}(Protocol):\n    """{doc}"""\n'
        )
    body = "\n\n".join(blocks)

    return f'''"""Public contracts for the {slug} module.

Other modules import from here only — never from implementations.
"""

from __future__ import annotations

from typing import Protocol, runtime_checkable


{body}'''


def _provider(config: ModuleConfig) -> str:
    slug = config.name
    title = module_title(slug)
    class_name = provider_class_name(slug)

    priority = config.provider_priority
    priority_line = (
        f"\n    priority = ProviderPriority.{priority}\n"
        if priority != "DOMAIN"
        else ""
    )
    priority_import = (
        "from lexigram.di.provider import Provider, ProviderPriority"
        if priority != "DOMAIN"
        else "from lexigram.di.provider import Provider"
    )

    health = ""
    if config.health:
        health = f'''
    async def health_check(self) -> bool:
        """Report whether the {slug} module can serve traffic."""
        return True
'''

    exports_doc = ""
    if config.exports:
        bound = "".join(
            f"\n    * ``{e.protocol}`` -> ``{e.implementation}``"
            for e in config.exports
        )
        exports_doc = f"\n\n    Binds this module's public surface:{bound}\n    "

    return f'''"""DI provider for the {slug} module."""

from __future__ import annotations

{priority_import}


class {class_name}(Provider):
    """Registers and boots {slug} services.{exports_doc}"""
{priority_line}{health}'''

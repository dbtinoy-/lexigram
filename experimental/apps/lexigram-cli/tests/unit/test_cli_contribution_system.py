from __future__ import annotations

import pytest

from lexigram.cli.registry.generator import GeneratorRegistry
from lexigram.contracts.cli.protocols import CliContributorProtocol
from lexigram.contracts.cli.types import GeneratorDefinition


class TestCliContracts:
    def test_generator_definition_is_frozen(self) -> None:
        gen = GeneratorDefinition(
            name="model",
            title="Generate Model",
            description="Scaffolds a domain model",
            contributor="core",
            generator_path="tests.fake:FakeGenerator",
        )
        with pytest.raises(AttributeError):
            gen.name = "other"  # type: ignore[misc]

    def test_generator_definition_defaults(self) -> None:
        gen = GeneratorDefinition(
            name="model",
            title="Generate Model",
            description="Scaffolds a domain model",
            contributor="core",
            generator_path="tests.fake:FakeGenerator",
        )
        assert gen.category == "general"
        assert gen.options == ()

    def test_cli_contributor_protocol_is_runtime_checkable(self) -> None:
        # isinstance() would raise TypeError if @runtime_checkable were missing
        assert isinstance(object(), CliContributorProtocol) is False

    def test_generator_definition_requires_generator_path(self) -> None:
        with pytest.raises(TypeError):
            GeneratorDefinition(
                name="model",
                title="Generate Model",
                description="Scaffolds a domain model",
                contributor="core",
            )


class TestGeneratorRegistryInstanceBased:
    def test_new_registry_is_empty(self) -> None:
        registry = GeneratorRegistry()
        assert registry.list_generators() == []

    def test_register_adds_generator(self) -> None:
        registry = GeneratorRegistry()
        gen = GeneratorDefinition(
            name="model",
            title="Generate Model",
            description="Scaffolds a domain model",
            contributor="core",
            generator_path="tests.fake:FakeGenerator",
        )
        registry.register(gen)
        assert len(registry.list_generators()) == 1
        assert registry.get("model") is gen

    def test_registry_instances_are_independent(self) -> None:
        r1 = GeneratorRegistry()
        r2 = GeneratorRegistry()
        gen = GeneratorDefinition(
            name="x",
            title="X",
            description="X",
            contributor="c",
            generator_path="tests.fake:FakeGenerator",
        )
        r1.register(gen)
        assert r2.list_generators() == []  # r2 must not see r1's generators


from lexigram.cli.contributors.base import BaseCliContributor
from lexigram.cli.contributors.registry import CliContributorRegistry


class TestBaseCliContributor:
    def test_base_contributor_has_contributor_id(self) -> None:
        class MyContributor(BaseCliContributor):
            @property
            def contributor_id(self) -> str:
                return "my_contrib"

        contrib = MyContributor()
        assert contrib.contributor_id == "my_contrib"

    def test_base_contributor_get_generators_returns_empty(self) -> None:
        class MyContributor(BaseCliContributor):
            @property
            def contributor_id(self) -> str:
                return "my_contrib"

        contrib = MyContributor()
        assert contrib.get_generators() == []


class TestCliContributorRegistry:
    def test_new_registry_is_empty(self) -> None:
        registry = CliContributorRegistry()
        assert registry.get_all() == []

    def test_register_contributor(self) -> None:
        class MyContributor(BaseCliContributor):
            @property
            def contributor_id(self) -> str:
                return "test"

            def get_generators(self):
                return []

        registry = CliContributorRegistry()
        contrib = MyContributor()
        registry.register(contrib)
        assert len(registry.get_all()) == 1

    def test_registry_instances_are_independent(self) -> None:
        class MyContributor(BaseCliContributor):
            @property
            def contributor_id(self) -> str:
                return "test"

        r1 = CliContributorRegistry()
        r2 = CliContributorRegistry()
        r1.register(MyContributor())
        assert r2.get_all() == []


from lexigram.cli.contributors.core import _CORE_GENERATOR_DATA, CoreCliContributor

# The set of generator names expected from _CORE_GENERATOR_DATA.
_EXPECTED_CORE_NAMES: frozenset[str] = frozenset(
    name for name, _ in _CORE_GENERATOR_DATA
)


class TestCoreCliContributor:
    def test_core_contributor_id_is_core(self) -> None:
        """contributor_id must return the string 'core'."""
        contrib = CoreCliContributor()
        assert contrib.contributor_id == "core"

    def test_core_contributor_get_generators_returns_list_of_generator_definitions(
        self,
    ) -> None:
        """get_generators() must return a list of GeneratorDefinition instances."""
        from lexigram.contracts.cli.types import GeneratorDefinition

        contrib = CoreCliContributor()
        generators = contrib.get_generators()
        assert isinstance(generators, list)
        assert len(generators) > 0
        for item in generators:
            assert isinstance(item, GeneratorDefinition)

    def test_core_contributor_generator_names_match_expected(self) -> None:
        """Generator names must exactly match the _CORE_ADAPTERS mapping."""
        contrib = CoreCliContributor()
        actual_names = {g.name for g in contrib.get_generators()}
        assert actual_names == _EXPECTED_CORE_NAMES

    def test_core_contributor_does_not_expose_moved_web_or_sql_generators(self) -> None:
        contrib = CoreCliContributor()
        actual_names = {g.name for g in contrib.get_generators()}

        assert actual_names.isdisjoint(
            {
                "controller",
                "resource",
                "middleware",
                "graphql",
                "webhook",
                "websocket",
                "repository",
                "filter",
                "seeder",
                "health",
            }
        )

    def test_core_contributor_does_not_include_moved_generators(self) -> None:
        contrib = CoreCliContributor()
        names = {g.name for g in contrib.get_generators()}

        assert "model" not in names
        assert "service" not in names
        assert "event" not in names
        assert "command" not in names
        assert "query" not in names
        assert "guard" not in names

    def test_core_contributor_get_generators_returns_fresh_list(self) -> None:
        """Each call to get_generators() returns an independent list."""
        contrib = CoreCliContributor()
        first = contrib.get_generators()
        second = contrib.get_generators()
        assert first == second
        assert first is not second

    def test_with_defaults_registry_contains_core_generators(self) -> None:
        """GeneratorRegistry.with_defaults() must be pre-populated with all core generators."""
        registry = GeneratorRegistry.with_defaults()
        registered_names = {g.name for g in registry.list_generators()}
        assert registered_names == _EXPECTED_CORE_NAMES

    def test_with_defaults_registry_is_independent_of_bare_registry(self) -> None:
        """with_defaults() must not affect a bare GeneratorRegistry()."""
        bare = GeneratorRegistry()
        _ = GeneratorRegistry.with_defaults()
        assert bare.list_generators() == []


import typer

from lexigram.cli.assembly import CommandAssembler


def _make_gen_def(name: str, contributor: str = "test") -> GeneratorDefinition:
    return GeneratorDefinition(
        name=name,
        title=name.capitalize(),
        description=f"Generate {name}",
        contributor=contributor,
        generator_path="tests.fake:FakeGenerator",
    )


class _FakeContributor:
    """Minimal CliContributorProtocol-compatible stub."""

    def __init__(self, contributor_id: str, gen_names: list[str]) -> None:
        self._contributor_id = contributor_id
        self._gen_names = gen_names

    @property
    def contributor_id(self) -> str:
        return self._contributor_id

    def get_generators(self) -> list[GeneratorDefinition]:
        return [_make_gen_def(n, self._contributor_id) for n in self._gen_names]


class TestCommandAssembler:
    def test_assemble_registers_commands_for_all_generators(self) -> None:
        """assemble() must register one Typer command per generator across all contributors."""
        contributor_registry = CliContributorRegistry()
        contributor_registry.register(_FakeContributor("plugin-a", ["alpha", "beta"]))
        contributor_registry.register(_FakeContributor("plugin-b", ["gamma"]))

        generator_registry = GeneratorRegistry()

        assembler = CommandAssembler(contributor_registry, generator_registry)
        app = typer.Typer()
        assembler.assemble(app)

        registered_names = {cmd.name for cmd in app.registered_commands}
        assert "alpha" in registered_names
        assert "beta" in registered_names
        assert "gamma" in registered_names
        assert len(app.registered_commands) == 3

    def test_assemble_with_empty_registry_registers_no_commands(self) -> None:
        """assemble() against an empty contributor registry must add no commands."""
        contributor_registry = CliContributorRegistry()
        generator_registry = GeneratorRegistry()

        assembler = CommandAssembler(contributor_registry, generator_registry)
        app = typer.Typer()
        assembler.assemble(app)

        assert app.registered_commands == []

    def test_definition_command_executes_registry_loaded_adapter(
        self, tmp_path, monkeypatch
    ) -> None:
        """Assembler commands must execute using the generator definition metadata."""
        from pathlib import Path
        import sys
        from types import ModuleType

        from typer.testing import CliRunner

        from lexigram.cli.generators.base import GenerationResult

        module_name = "fake_cli_generator_module"
        module = ModuleType(module_name)

        class FakeGenerator:
            def __init__(self, output_dir: str = "src") -> None:
                self.output_dir = output_dir

            def generate(self, name: str, **_: object) -> GenerationResult:
                result = GenerationResult()
                result.files_created.append(Path(self.output_dir) / f"{name}.py")
                return result

        module.FakeGenerator = FakeGenerator
        sys.modules[module_name] = module

        gen_def = GeneratorDefinition(
            name="widget",
            title="Widget",
            description="Generate widget",
            contributor="plugin",
            generator_path=f"{module_name}:FakeGenerator",
            default_output_dir="src/widgets",
        )

        class _GeneratorContributor:
            @property
            def contributor_id(self) -> str:
                return "plugin"

            def get_generators(self) -> list[GeneratorDefinition]:
                return [gen_def]

        contributor_registry = CliContributorRegistry()
        contributor_registry.register(_GeneratorContributor())

        generator_registry = GeneratorRegistry()
        generator_registry.register(gen_def)

        assembler = CommandAssembler(contributor_registry, generator_registry)
        app = typer.Typer()
        assembler.assemble(app)

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(app, ["Gizmo"])

        assert result.exit_code == 0, result.output
        assert "Created: src/widgets/Gizmo.py" in result.output

        del sys.modules[module_name]


from unittest.mock import AsyncMock, MagicMock

from lexigram.cli.di.sub_providers.contributor import CliContributorSubProvider


class TestCliProviderWiring:
    def test_core_contributor_entry_point_declared(self) -> None:
        """The lexigram.cli.contributors entry-point group must be declared in pyproject.toml."""
        import pathlib
        import tomllib  # stdlib in 3.11+

        pyproject_path = pathlib.Path(__file__).parent.parent.parent / "pyproject.toml"
        data = tomllib.loads(pyproject_path.read_text())

        entry_points = data.get("project", {}).get("entry-points", {})
        group = entry_points.get("lexigram.cli.contributors", {})

        assert "core" in group, (
            "Expected 'core' key in [project.entry-points.\"lexigram.cli.contributors\"]"
        )
        assert group["core"] == "lexigram.cli.contributors.core:CoreCliContributor", (
            f"Expected entry point to point to CoreCliContributor, got: {group['core']!r}"
        )

    def test_cli_provider_composes_contributor_sub_provider(self) -> None:
        """CLIProvider must compose a CliContributorSubProvider instance."""
        from lexigram.cli.di.provider import CLIProvider

        provider = CLIProvider()
        assert hasattr(provider, "_contributor_sub_provider"), (
            "CLIProvider must hold a _contributor_sub_provider attribute"
        )
        assert isinstance(provider._contributor_sub_provider, CliContributorSubProvider)

    @pytest.mark.asyncio
    async def test_cli_provider_register_delegates_to_sub_provider(self) -> None:
        """CLIProvider.register() must delegate to CliContributorSubProvider.register()."""
        from unittest.mock import AsyncMock, patch

        from lexigram.cli.di.provider import CLIProvider
        from lexigram.cli.di.sub_providers.contributor import CliContributorSubProvider

        provider = CLIProvider()
        container = MagicMock()

        with patch.object(
            CliContributorSubProvider,
            "register",
            new_callable=AsyncMock,
        ) as mock_register:
            await provider.register(container)

        mock_register.assert_awaited_once_with(container)

    @pytest.mark.asyncio
    async def test_cli_provider_boot_delegates_to_sub_provider(self) -> None:
        """CLIProvider.boot() must delegate to CliContributorSubProvider.boot()."""
        from unittest.mock import AsyncMock, patch

        from lexigram.cli.di.provider import CLIProvider
        from lexigram.cli.di.sub_providers.contributor import CliContributorSubProvider

        provider = CLIProvider()
        container = MagicMock()

        with patch.object(
            CliContributorSubProvider,
            "boot",
            new_callable=AsyncMock,
        ) as mock_boot:
            await provider.boot(container)

        mock_boot.assert_awaited_once_with(container)


class TestCliContributorSubProvider:
    @pytest.mark.asyncio
    async def test_register_binds_registries(self) -> None:
        """register() must call singleton for contribution-system runtime types."""
        sub_provider = CliContributorSubProvider()
        container = MagicMock()

        await sub_provider.register(container)

        registered_types = {c.args[0] for c in container.singleton.call_args_list}
        assert CliContributorRegistry in registered_types
        assert GeneratorRegistry in registered_types
        assert CommandAssembler in registered_types
        assert CoreCliContributor not in registered_types

    @pytest.mark.asyncio
    async def test_boot_entry_point_registers_contributors_in_both_registries(
        self,
    ) -> None:
        """boot() must populate both registries from runtime discovery."""
        from unittest.mock import patch

        sub_provider = CliContributorSubProvider()
        contributor_registry = CliContributorRegistry()
        generator_registry = GeneratorRegistry()

        async def _resolve(service_type: type) -> object:
            if service_type is CliContributorRegistry:
                return contributor_registry
            if service_type is GeneratorRegistry:
                return generator_registry
            raise ValueError(f"Unexpected resolve for {service_type}")

        container = MagicMock()
        container.resolve = AsyncMock(side_effect=_resolve)

        with patch(
            "lexigram.cli.di.sub_providers.contributor.populate_cli_registries"
        ) as mock_populate:
            await sub_provider.boot(container)

        mock_populate.assert_called_once_with(contributor_registry, generator_registry)


# ---------------------------------------------------------------------------
# T13: plugin list command
# ---------------------------------------------------------------------------

from unittest.mock import MagicMock, patch

from typer.testing import CliRunner

from lexigram.cli.commands.contrib import app as plugin_app


class TestPluginListCommand:
    """Tests for the ``lexigram plugin list`` entry-point discovery command."""

    def test_plugin_list_discovers_core_contributor(self) -> None:
        """plugin list must display contributor id and generator count for a discovered EP.

        Mocks ``importlib.metadata.entry_points`` inside the plugin command
        module to return a single fake entry point that loads
        ``CoreCliContributor``; asserts the output contains the contributor
        name ``"core"`` and the expected generator count.
        """
        from lexigram.cli.contributors.core import CoreCliContributor

        fake_ep = MagicMock()
        fake_ep.name = "core"
        fake_ep.load.return_value = CoreCliContributor

        runner = CliRunner()
        with patch(
            "lexigram.cli.contributors.runtime.entry_points",
            return_value=[fake_ep],
        ):
            result = runner.invoke(plugin_app, ["list"])

        assert result.exit_code == 0, result.output
        assert "core" in result.output
        assert "2" in result.output

    def test_plugin_list_shows_generator_names_preview(self) -> None:
        """plugin list must include at least the first generator name in the output."""
        from lexigram.cli.contributors.core import CoreCliContributor

        fake_ep = MagicMock()
        fake_ep.name = "core"
        fake_ep.load.return_value = CoreCliContributor

        runner = CliRunner()
        with patch(
            "lexigram.cli.contributors.runtime.entry_points",
            return_value=[fake_ep],
        ):
            result = runner.invoke(plugin_app, ["list"])

        assert result.exit_code == 0, result.output
        assert "provider" in result.output

    def test_plugin_list_with_no_contributors(self) -> None:
        """plugin list must gracefully report when no entry points are found."""
        runner = CliRunner()
        with patch(
            "lexigram.cli.contributors.runtime.entry_points",
            return_value=[],
        ):
            result = runner.invoke(plugin_app, ["list"])

        assert result.exit_code == 0, result.output
        assert "no" in result.output.lower() or "found" in result.output.lower()

    def test_plugin_list_handles_load_failure_gracefully(self) -> None:
        """plugin list must continue and report an error for a contributor that fails to load."""
        fake_ep = MagicMock()
        fake_ep.name = "broken"
        fake_ep.load.side_effect = ImportError("missing dependency")

        runner = CliRunner()
        with patch(
            "lexigram.cli.contributors.runtime.entry_points",
            return_value=[fake_ep],
        ):
            result = runner.invoke(plugin_app, ["list"])

        assert result.exit_code == 0, result.output
        assert "broken" in result.output
        assert "failed" in result.output.lower() or "missing" in result.output.lower()

    def test_plugin_list_multiple_contributors(self) -> None:
        """plugin list must list every contributor when multiple entry points are present."""
        from lexigram.contracts.cli.types import GeneratorDefinition

        class _AlphaContributor:
            @property
            def contributor_id(self) -> str:
                return "alpha"

            def get_generators(self) -> list[GeneratorDefinition]:
                return [
                    GeneratorDefinition(
                        name="thing",
                        title="Thing",
                        description="A thing",
                        contributor="alpha",
                        generator_path="tests.fake:FakeGenerator",
                    )
                ]

        class _BetaContributor:
            @property
            def contributor_id(self) -> str:
                return "beta"

            def get_generators(self) -> list[GeneratorDefinition]:
                return []

        ep_alpha = MagicMock()
        ep_alpha.name = "alpha"
        ep_alpha.load.return_value = _AlphaContributor

        ep_beta = MagicMock()
        ep_beta.name = "beta"
        ep_beta.load.return_value = _BetaContributor

        runner = CliRunner()
        with patch(
            "lexigram.cli.contributors.runtime.entry_points",
            return_value=[ep_alpha, ep_beta],
        ):
            result = runner.invoke(plugin_app, ["list"])

        assert result.exit_code == 0, result.output
        assert "alpha" in result.output
        assert "beta" in result.output


class TestCommandAssemblerPackageLayout:
    def test_definition_command_preserves_src_suffix_for_package_layout(
        self, tmp_path, monkeypatch
    ) -> None:
        from pathlib import Path
        import sys
        from types import ModuleType

        from typer.testing import CliRunner

        from lexigram.cli.generators.base import GenerationResult

        module_name = "fake_cli_package_layout_module"
        module = ModuleType(module_name)

        class FakeGenerator:
            def __init__(self, output_dir: str = "src") -> None:
                self.output_dir = output_dir

            def generate(self, name: str, **_: object) -> GenerationResult:
                result = GenerationResult()
                result.files_created.append(Path(self.output_dir) / f"{name}.py")
                return result

        module.FakeGenerator = FakeGenerator
        sys.modules[module_name] = module

        gen_def = GeneratorDefinition(
            name="model",
            title="Model",
            description="Generate model",
            contributor="plugin",
            generator_path=f"{module_name}:FakeGenerator",
            default_output_dir="src/models",
        )

        class _GeneratorContributor:
            @property
            def contributor_id(self) -> str:
                return "plugin"

            def get_generators(self) -> list[GeneratorDefinition]:
                return [gen_def]

        contributor_registry = CliContributorRegistry()
        contributor_registry.register(_GeneratorContributor())

        generator_registry = GeneratorRegistry()
        generator_registry.register(gen_def)

        assembler = CommandAssembler(contributor_registry, generator_registry)
        app = typer.Typer()
        assembler.assemble(app)

        runner = CliRunner()
        monkeypatch.chdir(tmp_path)
        try:
            package_dir = Path("src") / "petclinic"
            package_dir.mkdir(parents=True)
            (package_dir / "__init__.py").write_text("")
            result = runner.invoke(app, ["Gizmo"])
        finally:
            sys.modules.pop(module_name, None)

        assert result.exit_code == 0, result.output
        assert "Created: src/petclinic/models/Gizmo.py" in result.output


class TestCliContributorDiscovery:
    def test_load_cli_contributors_skips_bad_entry_point_load(self, capsys) -> None:
        from unittest.mock import MagicMock, patch

        from lexigram.cli.contributors.discovery import load_cli_contributors

        class _HealthyContributor:
            @property
            def contributor_id(self) -> str:
                return "healthy"

            def get_generators(self) -> list[GeneratorDefinition]:
                return []

        broken_entry_point = MagicMock()
        broken_entry_point.name = "broken-load"
        broken_entry_point.load.side_effect = ImportError("missing dependency")

        healthy_entry_point = MagicMock()
        healthy_entry_point.name = "healthy"
        healthy_entry_point.load.return_value = _HealthyContributor

        with patch(
            "lexigram.cli.contributors.runtime.entry_points",
            return_value=[broken_entry_point, healthy_entry_point],
        ):
            contributors = load_cli_contributors()

        assert [contributor.contributor_id for contributor in contributors] == [
            "healthy"
        ]
        captured = capsys.readouterr()
        assert "broken-load" in captured.out
        assert "missing dependency" in captured.out

    def test_load_cli_contributors_skips_bad_constructor(self, capsys) -> None:
        from unittest.mock import MagicMock, patch

        from lexigram.cli.contributors.discovery import load_cli_contributors

        class _BrokenContributor:
            def __init__(self) -> None:
                raise RuntimeError("constructor exploded")

        class _HealthyContributor:
            @property
            def contributor_id(self) -> str:
                return "healthy"

            def get_generators(self) -> list[GeneratorDefinition]:
                return []

        broken_entry_point = MagicMock()
        broken_entry_point.name = "broken-constructor"
        broken_entry_point.load.return_value = _BrokenContributor

        healthy_entry_point = MagicMock()
        healthy_entry_point.name = "healthy"
        healthy_entry_point.load.return_value = _HealthyContributor

        with patch(
            "lexigram.cli.contributors.runtime.entry_points",
            return_value=[broken_entry_point, healthy_entry_point],
        ):
            contributors = load_cli_contributors()

        assert [contributor.contributor_id for contributor in contributors] == [
            "healthy"
        ]
        captured = capsys.readouterr()
        assert "broken-constructor" in captured.out
        assert "constructor exploded" in captured.out

    def test_gen_module_reload_tolerates_broken_contributor(self, capsys) -> None:
        import importlib
        from unittest.mock import MagicMock, patch

        from typer.testing import CliRunner

        from lexigram.cli.commands import gen as gen_module

        broken_entry_point = MagicMock()
        broken_entry_point.name = "broken-load"
        broken_entry_point.load.side_effect = ImportError("missing dependency")

        try:
            with patch(
                "lexigram.cli.contributors.runtime.entry_points",
                return_value=[broken_entry_point],
            ):
                reloaded_module = importlib.reload(gen_module)

            runner = CliRunner()
            result = runner.invoke(reloaded_module.app, [])

            assert result.exit_code == 0, result.output
            assert "No generators discovered" in result.output
            captured = capsys.readouterr()
            assert "broken-load" in captured.out
            assert "missing dependency" in captured.out
        finally:
            importlib.reload(gen_module)


# ---------------------------------------------------------------------------
# T14: CacheCliContributor runtime discovery via populate_cli_registries
# ---------------------------------------------------------------------------


class TestCacheCliContributorDiscovery:
    """Verify populate_cli_registries wires CacheCliContributor into both registries."""

    @pytest.mark.asyncio
    async def test_populate_registers_cache_repo_generator(self) -> None:
        """populate_cli_registries with CacheCliContributor must register cache_repo."""
        from lexigram.cache.cli.contributor import CacheCliContributor
        from lexigram.cli.contributors.discovery import populate_cli_registries
        from lexigram.cli.contributors.registry import CliContributorRegistry
        from lexigram.cli.registry.generator import GeneratorRegistry

        contributor_registry = CliContributorRegistry()
        generator_registry = GeneratorRegistry()

        populate_cli_registries(
            contributor_registry,
            generator_registry,
            contributors=[CacheCliContributor()],
        )

        assert contributor_registry.get("cache") is not None
        assert generator_registry.get("cache_repo") is not None

    def test_cache_contributor_generator_path_points_to_package_local(self) -> None:
        """CacheCliContributor's generator_path must point to lexigram.cache, not lexigram.cli."""
        from lexigram.cache.cli.contributor import CacheCliContributor

        contributor = CacheCliContributor()
        definitions = {g.name: g for g in contributor.get_generators()}

        assert "cache_repo" in definitions
        path = definitions["cache_repo"].generator_path
        assert path.startswith("lexigram.cache."), (
            f"generator_path must be in lexigram.cache package, got: {path}"
        )
        assert "lexigram.cli" not in path

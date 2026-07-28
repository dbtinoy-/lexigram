"""Integration tests for CompiledModuleGraph reflection API.

Tests the five reflection methods on a realistic multi-module graph:
- get_module_by_name
- get_exports_for_module
- get_importing_modules
- get_dependency_chain
- get_boot_level

Uses a 3-module chain: CoreModule → CacheModule → WebModule
"""

from __future__ import annotations

import pytest

from lexigram.contracts.core.di import ContainerRegistrarProtocol
from lexigram.di.module import DynamicModule, Module, ModuleCompiler, module
from lexigram.di.provider import Provider, ProviderPriority

# ---------------------------------------------------------------------------
# Minimal service markers
# ---------------------------------------------------------------------------


class CoreService:
    """Marker type for core service exports."""


class CacheService:
    """Marker type for cache service exports."""


class WebHandler:
    """Marker type for web handler exports."""


# ---------------------------------------------------------------------------
# Minimal provider stubs
# ---------------------------------------------------------------------------


class _CoreProvider(Provider):
    name = "core_provider"
    priority = ProviderPriority.NORMAL

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        pass


class _CacheProvider(Provider):
    name = "cache_provider"
    priority = ProviderPriority.NORMAL

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        pass


class _WebProvider(Provider):
    name = "web_provider"
    priority = ProviderPriority.NORMAL

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        pass


# ---------------------------------------------------------------------------
# Module definitions
# ---------------------------------------------------------------------------


@module(providers=[_CoreProvider], exports=[CoreService])
class CoreModule(Module):
    @classmethod
    def configure(cls) -> DynamicModule:
        return DynamicModule(
            module=cls,
            providers=[_CoreProvider],
            exports=[CoreService],
        )


@module(providers=[_CacheProvider], imports=[CoreModule], exports=[CacheService])
class CacheModule(Module):
    @classmethod
    def configure(cls) -> DynamicModule:
        return DynamicModule(
            module=cls,
            providers=[_CacheProvider],
            imports=[CoreModule],
            exports=[CacheService],
        )


@module(
    providers=[_WebProvider],
    imports=[CoreModule, CacheModule],
    exports=[WebHandler],
)
class WebModule(Module):
    @classmethod
    def configure(cls) -> DynamicModule:
        return DynamicModule(
            module=cls,
            providers=[_WebProvider],
            imports=[CoreModule, CacheModule],
            exports=[WebHandler],
        )


# ---------------------------------------------------------------------------
# Fixture
# ---------------------------------------------------------------------------


@pytest.fixture
def graph():
    """Compile the 3-module graph with WebModule as root."""
    return ModuleCompiler().compile([WebModule])


# ---------------------------------------------------------------------------
# TestGetModuleByName
# ---------------------------------------------------------------------------


class TestGetModuleByNameIntegration:
    """Test finding modules by name in a realistic multi-module graph."""

    def test_finds_core_module(self, graph) -> None:
        """get_module_by_name should find CoreModule."""
        result = graph.get_module_by_name("CoreModule")
        assert result is CoreModule

    def test_finds_cache_module(self, graph) -> None:
        """get_module_by_name should find CacheModule."""
        result = graph.get_module_by_name("CacheModule")
        assert result is CacheModule

    def test_finds_web_module(self, graph) -> None:
        """get_module_by_name should find WebModule."""
        result = graph.get_module_by_name("WebModule")
        assert result is WebModule

    def test_returns_none_for_missing(self, graph) -> None:
        """get_module_by_name should return None for non-existent modules."""
        result = graph.get_module_by_name("DoesNotExist")
        assert result is None

    def test_name_matching_is_exact(self, graph) -> None:
        """get_module_by_name should use exact name matching."""
        result = graph.get_module_by_name("Core")
        assert result is None

    def test_case_sensitive_matching(self, graph) -> None:
        """get_module_by_name should be case-sensitive."""
        result = graph.get_module_by_name("coremodule")
        assert result is None


# ---------------------------------------------------------------------------
# TestGetExportsForModule
# ---------------------------------------------------------------------------


class TestGetExportsForModuleIntegration:
    """Test querying module exports in a realistic graph."""

    def test_core_exports_core_service(self, graph) -> None:
        """CoreModule should export CoreService."""
        exports = graph.get_exports_for_module(CoreModule)
        assert CoreService in exports

    def test_cache_exports_cache_service(self, graph) -> None:
        """CacheModule should export CacheService."""
        exports = graph.get_exports_for_module(CacheModule)
        assert CacheService in exports

    def test_web_exports_web_handler(self, graph) -> None:
        """WebModule should export WebHandler."""
        exports = graph.get_exports_for_module(WebModule)
        assert WebHandler in exports

    def test_exports_returns_frozenset(self, graph) -> None:
        """get_exports_for_module should return a frozenset."""
        exports = graph.get_exports_for_module(CoreModule)
        assert isinstance(exports, frozenset)

    def test_exports_are_immutable(self, graph) -> None:
        """Exports should be immutable (frozenset)."""
        exports = graph.get_exports_for_module(WebModule)
        with pytest.raises(AttributeError):
            exports.add(CoreService)

    def test_unknown_module_returns_empty(self, graph) -> None:
        """get_exports_for_module should return empty frozenset for unknown modules."""

        class UnknownModule:
            pass

        exports = graph.get_exports_for_module(UnknownModule)
        assert len(exports) == 0
        assert isinstance(exports, frozenset)

    def test_exports_count_matches_declaration(self, graph) -> None:
        """Each module should export exactly what was declared."""
        core_exports = graph.get_exports_for_module(CoreModule)
        cache_exports = graph.get_exports_for_module(CacheModule)
        web_exports = graph.get_exports_for_module(WebModule)

        assert len(core_exports) == 1
        assert len(cache_exports) == 1
        assert len(web_exports) == 1


# ---------------------------------------------------------------------------
# TestGetImportingModules
# ---------------------------------------------------------------------------


class TestGetImportingModulesIntegration:
    """Test querying which modules import a given module."""

    def test_core_module_imported_by_cache(self, graph) -> None:
        """CoreModule should be imported by CacheModule."""
        importers = graph.get_importing_modules(CoreModule)
        assert CacheModule in importers

    def test_core_module_imported_by_web(self, graph) -> None:
        """CoreModule should be imported by WebModule."""
        importers = graph.get_importing_modules(CoreModule)
        assert WebModule in importers

    def test_core_module_imported_by_both_cache_and_web(self, graph) -> None:
        """CoreModule should be imported by both CacheModule and WebModule."""
        importers = graph.get_importing_modules(CoreModule)
        assert CacheModule in importers
        assert WebModule in importers
        assert len(importers) == 2

    def test_cache_module_imported_by_web(self, graph) -> None:
        """CacheModule should be imported by WebModule."""
        importers = graph.get_importing_modules(CacheModule)
        assert WebModule in importers

    def test_cache_module_not_imported_by_core(self, graph) -> None:
        """CacheModule should NOT be imported by CoreModule."""
        importers = graph.get_importing_modules(CacheModule)
        assert CoreModule not in importers

    def test_web_module_not_imported_by_anyone(self, graph) -> None:
        """WebModule (the root) should not be imported by anyone."""
        importers = graph.get_importing_modules(WebModule)
        assert len(importers) == 0

    def test_importing_modules_returns_frozenset(self, graph) -> None:
        """get_importing_modules should return a frozenset."""
        importers = graph.get_importing_modules(CoreModule)
        assert isinstance(importers, frozenset)

    def test_importing_modules_is_immutable(self, graph) -> None:
        """Importing modules set should be immutable."""
        importers = graph.get_importing_modules(CoreModule)
        with pytest.raises(AttributeError):
            importers.add(WebModule)

    def test_unknown_module_returns_empty(self, graph) -> None:
        """get_importing_modules should return empty frozenset for unknown modules."""

        class UnknownModule:
            pass

        importers = graph.get_importing_modules(UnknownModule)
        assert len(importers) == 0
        assert isinstance(importers, frozenset)


# ---------------------------------------------------------------------------
# TestGetDependencyChain
# ---------------------------------------------------------------------------


class TestGetDependencyChainIntegration:
    """Test querying dependency chains in the multi-module graph."""

    def test_core_module_has_no_dependencies(self, graph) -> None:
        """CoreModule (leaf) should have an empty dependency chain."""
        chain = graph.get_dependency_chain(CoreModule)
        assert chain == []

    def test_cache_module_depends_on_core(self, graph) -> None:
        """CacheModule should depend on CoreModule."""
        chain = graph.get_dependency_chain(CacheModule)
        assert len(chain) == 1
        assert CoreModule in chain

    def test_web_module_dependency_chain_includes_cache_and_core(self, graph) -> None:
        """WebModule dependency chain should include CacheModule and CoreModule."""
        chain = graph.get_dependency_chain(WebModule)
        assert CacheModule in chain
        assert CoreModule in chain
        # Should not include WebModule itself
        assert WebModule not in chain

    def test_dependency_chain_bfs_order(self, graph) -> None:
        """Dependency chain should be in BFS order (direct deps first)."""
        chain = graph.get_dependency_chain(WebModule)
        # Direct imports of WebModule: CoreModule, CacheModule (in that order)
        # Their imports: CoreModule has no imports, CacheModule imports CoreModule
        # BFS should visit direct imports first, in declaration order
        # So: CoreModule (direct), then CacheModule (direct)
        assert CoreModule in chain
        assert CacheModule in chain
        # Both are direct imports, so they should both appear before any transitive imports
        # The order respects the declaration order in WebModule.imports
        assert chain.index(CoreModule) == 0

    def test_dependency_chain_does_not_include_root(self, graph) -> None:
        """Dependency chain should not include the root module itself."""
        chain = graph.get_dependency_chain(WebModule)
        assert WebModule not in chain

    def test_unknown_module_returns_empty_list(self, graph) -> None:
        """get_dependency_chain should return empty list for unknown modules."""

        class UnknownModule:
            pass

        chain = graph.get_dependency_chain(UnknownModule)
        assert chain == []
        assert isinstance(chain, list)

    def test_dependency_chain_returns_list_type(self, graph) -> None:
        """get_dependency_chain should return a list (not frozenset)."""
        chain = graph.get_dependency_chain(WebModule)
        assert isinstance(chain, list)


# ---------------------------------------------------------------------------
# TestGetBootLevel
# ---------------------------------------------------------------------------


class TestGetBootLevelIntegration:
    """Test boot level ordering in the multi-module graph."""

    def test_core_module_has_boot_level(self, graph) -> None:
        """CoreModule should have a defined boot level."""
        level = graph.get_boot_level(CoreModule)
        assert level is not None
        assert isinstance(level, int)

    def test_cache_module_has_boot_level(self, graph) -> None:
        """CacheModule should have a defined boot level."""
        level = graph.get_boot_level(CacheModule)
        assert level is not None
        assert isinstance(level, int)

    def test_web_module_has_boot_level(self, graph) -> None:
        """WebModule should have a defined boot level."""
        level = graph.get_boot_level(WebModule)
        assert level is not None
        assert isinstance(level, int)

    def test_core_boots_first(self, graph) -> None:
        """CoreModule (no imports) should boot first."""
        core_level = graph.get_boot_level(CoreModule)
        cache_level = graph.get_boot_level(CacheModule)
        web_level = graph.get_boot_level(WebModule)

        assert core_level is not None
        assert cache_level is not None
        assert web_level is not None

        # Core has no imports, so it boots first
        assert core_level <= cache_level
        assert core_level <= web_level

    def test_cache_boots_before_or_with_web(self, graph) -> None:
        """CacheModule should boot before or with WebModule."""
        cache_level = graph.get_boot_level(CacheModule)
        web_level = graph.get_boot_level(WebModule)

        assert cache_level is not None
        assert web_level is not None
        assert cache_level <= web_level

    def test_boot_levels_are_non_negative(self, graph) -> None:
        """Boot levels should be non-negative integers."""
        core_level = graph.get_boot_level(CoreModule)
        cache_level = graph.get_boot_level(CacheModule)
        web_level = graph.get_boot_level(WebModule)

        assert core_level is not None
        assert core_level >= 0
        assert cache_level is not None
        assert cache_level >= 0
        assert web_level is not None
        assert web_level >= 0

    def test_unknown_module_returns_none(self, graph) -> None:
        """get_boot_level should return None for unknown modules."""

        class UnknownModule:
            pass

        level = graph.get_boot_level(UnknownModule)
        assert level is None

    def test_boot_levels_reflect_dependency_order(self, graph) -> None:
        """Modules with more dependencies should have higher boot levels."""
        core_level = graph.get_boot_level(CoreModule)
        cache_level = graph.get_boot_level(CacheModule)

        # CacheModule depends on CoreModule, so it should boot at or after
        assert core_level is not None
        assert cache_level is not None
        assert core_level <= cache_level


# ---------------------------------------------------------------------------
# Cross-Method Integration Tests
# ---------------------------------------------------------------------------


class TestCrossMethodIntegration:
    """Test interactions between multiple reflection methods."""

    def test_get_module_by_name_and_get_exports_match(self, graph) -> None:
        """Module found via get_module_by_name should match get_exports_for_module."""
        module_cls = graph.get_module_by_name("CoreModule")
        assert module_cls is CoreModule

        exports = graph.get_exports_for_module(CoreModule)
        assert CoreService in exports

    def test_importers_and_dependency_chain_are_inverse(self, graph) -> None:
        """If X is in Y's dependency chain, then Y should be in X's importers."""
        cache_chain = graph.get_dependency_chain(CacheModule)
        core_importers = graph.get_importing_modules(CoreModule)

        assert CoreModule in cache_chain
        assert CacheModule in core_importers

    def test_boot_level_respects_import_structure(self, graph) -> None:
        """Boot levels should strictly respect import dependencies."""
        core_level = graph.get_boot_level(CoreModule)
        cache_level = graph.get_boot_level(CacheModule)
        web_level = graph.get_boot_level(WebModule)

        # Core has no imports
        assert core_level is not None
        assert core_level >= 0

        # Cache imports Core
        assert cache_level is not None
        assert core_level <= cache_level

        # Web imports both Core and Cache
        assert web_level is not None
        assert core_level <= web_level
        assert cache_level <= web_level

    def test_exports_and_importing_modules_are_consistent(self, graph) -> None:
        """Modules that import a module should have access to its exports."""
        cache_importers = graph.get_importing_modules(CacheModule)
        cache_exports = graph.get_exports_for_module(CacheModule)

        assert WebModule in cache_importers
        assert CacheService in cache_exports

        # Verify WebModule node exists and is in the graph
        web_node = graph.get_module(WebModule)
        assert web_node is not None

    def test_graph_structure_consistency(self, graph) -> None:
        """Verify graph structure is internally consistent."""
        # All modules in graph should be findable by name
        for module_cls in [CoreModule, CacheModule, WebModule]:
            name = module_cls.__name__
            result = graph.get_module_by_name(name)
            assert result is module_cls

        # All modules with providers should have a boot level
        for module_cls in [CoreModule, CacheModule, WebModule]:
            level = graph.get_boot_level(module_cls)
            assert level is not None, f"{module_cls.__name__} should have a boot level"

    def test_dependency_relationships_form_dag(self, graph) -> None:
        """Dependency relationships should form a DAG (no cycles)."""
        # If A imports B and B imports C, then A should not import C directly
        # and C should not import A (acyclic)

        web_deps = set(graph.get_dependency_chain(WebModule))
        cache_deps = set(graph.get_dependency_chain(CacheModule))
        core_deps = set(graph.get_dependency_chain(CoreModule))

        # No cycles: if WebModule imports CacheModule, CacheModule should not import WebModule
        assert WebModule not in cache_deps
        assert WebModule not in core_deps

        # No cycles: if CacheModule imports CoreModule, CoreModule should not import CacheModule
        assert CacheModule not in core_deps

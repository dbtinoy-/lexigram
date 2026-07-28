"""Tests for lexigram-ai CLI modules.

Covers:
    - lexigram.ai.cli.checks     (check_llm_provider, check_subsystem_discovery)
    - lexigram.ai.cli.commands   (create_ai_app)
    - lexigram.ai.cli.contributor (AICliContributor)
    - lexigram.ai.cli.doctor     (check_ai_api_keys)
    - lexigram.ai.cli.shell      (provide_ai_client)
    - lexigram.ai.decorators     (import coverage)
    - lexigram.ai.events         (import coverage)
    - lexigram.ai.hooks          (import coverage)
    - lexigram.ai.protocols      (import coverage)
    - lexigram.ai.module         (AIModule.stub)
"""

from __future__ import annotations

import os
from unittest.mock import AsyncMock, MagicMock

import pytest


# ---------------------------------------------------------------------------
# cli/checks.py
# ---------------------------------------------------------------------------


class TestCLIChecks:
    """Tests for lexigram.ai.cli.checks."""

    @pytest.mark.asyncio
    async def test_check_llm_provider_returns_healthy_dict(self) -> None:
        """check_llm_provider returns a status dict with 'healthy' status."""
        from lexigram.ai.cli.checks import check_llm_provider

        container = MagicMock()
        result = await check_llm_provider(container)

        assert isinstance(result, dict)
        assert result["status"] == "healthy"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_check_subsystem_discovery_returns_healthy_dict(self) -> None:
        """check_subsystem_discovery returns a status dict with 'healthy' status."""
        from lexigram.ai.cli.checks import check_subsystem_discovery

        container = MagicMock()
        result = await check_subsystem_discovery(container)

        assert isinstance(result, dict)
        assert result["status"] == "healthy"
        assert "message" in result

    @pytest.mark.asyncio
    async def test_checks_accept_any_container_object(self) -> None:
        """Both check functions accept arbitrary container objects (duck-typed)."""
        from lexigram.ai.cli.checks import check_llm_provider, check_subsystem_discovery

        # Passes with a plain object — interface is duck-typed
        r1 = await check_llm_provider(object())
        r2 = await check_subsystem_discovery(object())
        assert r1["status"] == "healthy"
        assert r2["status"] == "healthy"


# ---------------------------------------------------------------------------
# cli/commands.py
# ---------------------------------------------------------------------------


class TestCLICommands:
    """Tests for lexigram.ai.cli.commands.create_ai_app."""

    def test_create_ai_app_returns_typer_app(self) -> None:
        """create_ai_app() returns a Typer application."""
        typer = pytest.importorskip("typer", reason="typer not installed")
        from lexigram.ai.cli.commands import create_ai_app

        app = create_ai_app()
        assert app is not None

    def test_create_ai_app_has_models_subgroup(self) -> None:
        """create_ai_app() registers a 'models' sub-command group."""
        pytest.importorskip("typer", reason="typer not installed")
        from lexigram.ai.cli.commands import create_ai_app

        app = create_ai_app()
        group_names = [g.name for g in app.registered_groups]
        assert "models" in group_names

    def test_create_ai_app_has_providers_subgroup(self) -> None:
        """create_ai_app() registers a 'providers' sub-command group."""
        pytest.importorskip("typer", reason="typer not installed")
        from lexigram.ai.cli.commands import create_ai_app

        app = create_ai_app()
        group_names = [g.name for g in app.registered_groups]
        assert "providers" in group_names

    def test_create_ai_app_has_status_command(self) -> None:
        """create_ai_app() registers a 'status' command."""
        pytest.importorskip("typer", reason="typer not installed")
        from lexigram.ai.cli.commands import create_ai_app

        app = create_ai_app()
        command_names = [cmd.name for cmd in app.registered_commands]
        assert "status" in command_names

    def test_create_ai_app_has_config_command(self) -> None:
        """create_ai_app() registers a 'config' command."""
        pytest.importorskip("typer", reason="typer not installed")
        from lexigram.ai.cli.commands import create_ai_app

        app = create_ai_app()
        command_names = [cmd.name for cmd in app.registered_commands]
        assert "config" in command_names

    def test_create_ai_app_has_test_command(self) -> None:
        """create_ai_app() registers a 'test' command."""
        pytest.importorskip("typer", reason="typer not installed")
        from lexigram.ai.cli.commands import create_ai_app

        app = create_ai_app()
        command_names = [cmd.name for cmd in app.registered_commands]
        assert "test" in command_names

    def test_create_ai_app_is_callable_multiple_times(self) -> None:
        """create_ai_app() can be called multiple times — it is a factory."""
        pytest.importorskip("typer", reason="typer not installed")
        from lexigram.ai.cli.commands import create_ai_app

        app1 = create_ai_app()
        app2 = create_ai_app()
        assert app1 is not app2  # fresh instance each call

    def test_ai_commands_execution(self) -> None:
        """Execute AI CLI commands to cover the function bodies."""
        typer = pytest.importorskip("typer", reason="typer not installed")
        from typer.testing import CliRunner
        from lexigram.ai.cli.commands import create_ai_app

        app = create_ai_app()
        runner = CliRunner()

        # Test 'status'
        result = runner.invoke(app, ["status"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.stdout

        # Test 'models list'
        result = runner.invoke(app, ["models", "list"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.stdout

        # Test 'providers list'
        result = runner.invoke(app, ["providers", "list"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.stdout

        # Test 'config'
        result = runner.invoke(app, ["config"])
        assert result.exit_code == 0
        assert "not yet implemented" in result.stdout

        # Test 'test'
        result = runner.invoke(app, ["test", "openai"])
        assert result.exit_code == 0
        assert "Testing provider 'openai'" in result.stdout


# ---------------------------------------------------------------------------
# cli/contributor.py
# ---------------------------------------------------------------------------


class TestAICliContributor:
    """Tests for AICliContributor enum-based CLI contributor.

    AICliContributor is a str Enum with no members (empty enum body).
    Its instance methods are tested by calling them unbound, passing None
    as self — which matches how Python resolves unbound method calls on an
    empty Enum class.
    """

    def test_contributor_id_returns_ai(self) -> None:
        """contributor_id always returns 'ai'."""
        from lexigram.ai.cli.contributor import AICliContributor

        assert AICliContributor.contributor_id.fget(None) == "ai"

    def test_get_generators_returns_empty_list(self) -> None:
        """get_generators() returns an empty list."""
        from lexigram.ai.cli.contributor import AICliContributor

        result = AICliContributor.get_generators(None)
        assert result == []

    def test_get_commands_returns_ai_command_contribution(self) -> None:
        """get_commands() returns a list with the 'ai' command contribution."""
        from lexigram.ai.cli.contributor import AICliContributor

        commands = AICliContributor.get_commands(None)

        assert len(commands) == 1
        assert commands[0].name == "ai"
        assert commands[0].contributor == "ai"
        assert commands[0].category == "ai"

    def test_get_health_checks_returns_two_checks(self) -> None:
        """get_health_checks() returns exactly two health check contributions."""
        from lexigram.ai.cli.contributor import AICliContributor

        checks = AICliContributor.get_health_checks(None)

        assert len(checks) == 2
        names = {c.name for c in checks}
        assert "ai_llm_provider" in names
        assert "ai_subsystem_discovery" in names

    def test_get_doctor_checks_returns_api_key_check(self) -> None:
        """get_doctor_checks() returns the API key doctor check."""
        from lexigram.ai.cli.contributor import AICliContributor

        checks = AICliContributor.get_doctor_checks(None)

        assert len(checks) == 1
        assert checks[0].name == "ai_api_keys_configured"
        assert checks[0].contributor == "ai"

    def test_get_shell_context_returns_ai_entry(self) -> None:
        """get_shell_context() returns a single AI client shell contribution."""
        from lexigram.ai.cli.contributor import AICliContributor

        ctx = AICliContributor.get_shell_context(None)

        assert len(ctx) == 1
        assert ctx[0].name == "ai"

    def test_get_hooks_returns_empty_list(self) -> None:
        """get_hooks() returns an empty list."""
        from lexigram.ai.cli.contributor import AICliContributor

        assert AICliContributor.get_hooks(None) == []


# ---------------------------------------------------------------------------
# cli/doctor.py
# ---------------------------------------------------------------------------


class TestCLIDoctor:
    """Tests for lexigram.ai.cli.doctor.check_ai_api_keys."""

    def test_returns_ok_when_openai_key_set(self, monkeypatch) -> None:
        """Returns 'ok' status when OPENAI_API_KEY is present."""
        from lexigram.ai.cli.doctor import check_ai_api_keys

        monkeypatch.setenv("OPENAI_API_KEY", "sk-test-key")
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        result = check_ai_api_keys()

        assert result["status"] == "ok"
        assert "OPENAI_API_KEY" in result["message"]

    def test_returns_ok_when_anthropic_key_set(self, monkeypatch) -> None:
        """Returns 'ok' status when ANTHROPIC_API_KEY is present."""
        from lexigram.ai.cli.doctor import check_ai_api_keys

        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-test")
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)

        result = check_ai_api_keys()

        assert result["status"] == "ok"
        assert "ANTHROPIC_API_KEY" in result["message"]

    def test_returns_ok_when_both_keys_set(self, monkeypatch) -> None:
        """Returns 'ok' and lists both keys when both env vars are set."""
        from lexigram.ai.cli.doctor import check_ai_api_keys

        monkeypatch.setenv("OPENAI_API_KEY", "sk-openai")
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-anthropic")

        result = check_ai_api_keys()

        assert result["status"] == "ok"
        assert "OPENAI_API_KEY" in result["message"]
        assert "ANTHROPIC_API_KEY" in result["message"]

    def test_returns_warning_when_no_keys_set(self, monkeypatch) -> None:
        """Returns 'warning' status when no AI API key env vars are set."""
        from lexigram.ai.cli.doctor import check_ai_api_keys

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        result = check_ai_api_keys()

        assert result["status"] == "warning"
        assert "No AI API keys" in result["message"]

    def test_result_is_dict(self, monkeypatch) -> None:
        """check_ai_api_keys always returns a dict."""
        from lexigram.ai.cli.doctor import check_ai_api_keys

        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)

        result = check_ai_api_keys()
        assert isinstance(result, dict)
        assert "status" in result
        assert "message" in result


# ---------------------------------------------------------------------------
# cli/shell.py
# ---------------------------------------------------------------------------


class TestCLIShell:
    """Tests for lexigram.ai.cli.shell.provide_ai_client."""

    @pytest.mark.asyncio
    async def test_provide_ai_client_calls_container_resolve(self) -> None:
        """provide_ai_client() delegates to container.resolve(LLMClientProtocol)."""
        from lexigram.ai.cli.shell import provide_ai_client
        from lexigram.contracts.ai.llm import LLMClientProtocol

        mock_client = MagicMock()
        container = MagicMock()
        container.resolve = AsyncMock(return_value=mock_client)

        result = await provide_ai_client(container)

        container.resolve.assert_awaited_once_with(LLMClientProtocol)
        assert result is mock_client

    @pytest.mark.asyncio
    async def test_provide_ai_client_propagates_resolution_error(self) -> None:
        """provide_ai_client() propagates errors from container.resolve()."""
        from lexigram.ai.cli.shell import provide_ai_client

        container = MagicMock()
        container.resolve = AsyncMock(side_effect=ValueError("LLM not registered"))

        with pytest.raises(ValueError, match="LLM not registered"):
            await provide_ai_client(container)


# ---------------------------------------------------------------------------
# Stub modules (decorators, events, hooks, protocols)
# ---------------------------------------------------------------------------


class TestStubModules:
    """Import-coverage tests for stub/placeholder modules."""

    def test_decorators_module_importable(self) -> None:
        """lexigram.ai.decorators can be imported without error."""
        import lexigram.ai.decorators  # noqa: F401

    def test_events_module_importable(self) -> None:
        """lexigram.ai.events can be imported without error."""
        import lexigram.ai.events  # noqa: F401

    def test_hooks_module_importable(self) -> None:
        """lexigram.ai.hooks can be imported without error."""
        import lexigram.ai.hooks  # noqa: F401

    def test_protocols_module_importable(self) -> None:
        """lexigram.ai.protocols can be imported without error."""
        import lexigram.ai.protocols  # noqa: F401


# ---------------------------------------------------------------------------
# AIModule.stub()
# ---------------------------------------------------------------------------


class TestAIModuleStub:
    """Tests for AIModule.stub() — no-op module for testing environments."""

    def test_stub_returns_dynamic_module(self) -> None:
        """stub() returns a DynamicModule instance."""
        from lexigram.ai.module import AIModule
        from lexigram.di.module import DynamicModule

        try:
            result = AIModule.stub()
            assert isinstance(result, DynamicModule)
        except ImportError:
            pytest.skip("One or more AI sub-packages not installed")

    def test_stub_exports_ai_provider_protocol(self) -> None:
        """stub() exports AIProviderProtocol."""
        from lexigram.ai.module import AIModule
        from lexigram.contracts.ai import AIProviderProtocol

        try:
            result = AIModule.stub()
            assert AIProviderProtocol in result.exports
        except ImportError:
            pytest.skip("One or more AI sub-packages not installed")

    def test_stub_module_is_ai_module(self) -> None:
        """stub() sets the module attribute to AIModule."""
        from lexigram.ai.module import AIModule

        try:
            result = AIModule.stub()
            assert result.module is AIModule
        except ImportError:
            pytest.skip("One or more AI sub-packages not installed")

    def test_stub_has_imports(self) -> None:
        """stub() includes at least one sub-module import."""
        from lexigram.ai.module import AIModule

        try:
            result = AIModule.stub()
            assert len(result.imports) > 0
        except ImportError:
            pytest.skip("One or more AI sub-packages not installed")

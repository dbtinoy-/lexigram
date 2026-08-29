"""Contributor contract tests for the audit CLI."""

from __future__ import annotations

import importlib
from pathlib import Path
import sys
import types
from typing import Any

from lexigram.audit.cli.contributor import AuditCliContributor
from lexigram.audit.cli.generators.audited import AuditedHandlerGenerator
from lexigram.contracts.cli.protocols import CliContributorProtocol


def test_audit_contributor_implements_protocol_shape() -> None:
    contributor = AuditCliContributor()

    assert isinstance(contributor, CliContributorProtocol)
    assert contributor.contributor_id == "audit"


def test_audit_contributor_exposes_expected_generators() -> None:
    contributor = AuditCliContributor()

    assert {definition.name for definition in contributor.get_generators()} == {
        "audited",
    }


def test_audit_contributor_paths_are_package_local() -> None:
    contributor = AuditCliContributor()

    assert {
        definition.generator_path for definition in contributor.get_generators()
    } == {
        "lexigram.audit.cli.generators.audited:AuditedHandlerGenerator",
    }


def test_audited_generator_defaults() -> None:
    generator = AuditedHandlerGenerator()

    assert generator.name == "audited"
    assert generator.default_output_dir == "src/audit"
    assert generator.description == "Generate an audited async handler"


def test_audited_handler_renders_and_runs(tmp_path: Path) -> None:
    generator = AuditedHandlerGenerator(output_dir=tmp_path)
    result = generator.generate(
        "update_user",
        output_dir=tmp_path,
        action="user.update",
        resource_type="User",
        severity="high",
    )

    assert len(result.files_created) == 1
    output = Path(result.files_created[0])
    assert output.name == "update_user_audited.py"

    module = types.ModuleType("update_user_audited")
    module.__file__ = str(output)
    sys.modules[module.__name__] = module
    try:
        spec = importlib.util.spec_from_file_location("update_user_audited", output)
        assert spec is not None
        assert spec.loader is not None
        module = importlib.util.module_from_spec(spec)
        sys.modules[module.__name__] = module
        spec.loader.exec_module(module)
        handler = module.UpdateUserAuditedHandler()
        result_data: dict[str, Any] = _run_coroutine(handler.execute, user_id="1")

        assert result_data == {"status": "ok", "user_id": "1"}
        execute = handler.execute
        assert execute.__audited__ is True  # type: ignore[attr-defined]
        assert execute.__audit_action__ == "user.update"  # type: ignore[attr-defined]
        assert execute.__audit_resource_type__ == "User"  # type: ignore[attr-defined]
        assert execute.__audit_severity__ == "high"  # type: ignore[attr-defined]
    finally:
        sys.modules.pop(module.__name__, None)


def _run_coroutine(coro: Any, **kwargs: Any) -> Any:
    """Run an async callable synchronously for a lightweight unit test."""
    import asyncio

    return asyncio.run(coro(**kwargs))


def test_audited_importable_from_package_root() -> None:
    module = importlib.import_module("lexigram.audit")

    assert callable(module.audited)

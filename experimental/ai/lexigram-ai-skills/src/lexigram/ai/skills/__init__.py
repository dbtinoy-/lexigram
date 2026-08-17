"""Lexigram AI Skills — composable, registry-based skill execution platform."""

from __future__ import annotations

import importlib.metadata
from typing import TYPE_CHECKING

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from lexigram.ai.skills.constants import __version__ as __version__

if TYPE_CHECKING:
    from lexigram.ai.skills.base import AbstractSkill
    from lexigram.ai.skills.executor import SkillExecutor
    from lexigram.ai.skills.hooks import (
        SkillExecutedHook,
        SkillExecutionFailedHook,
        SkillRegisteredHook,
    )
    from lexigram.ai.skills.registry import SkillRegistry

_LAZY_IMPORTS: dict[str, str] = {
    # --- Base ---
    "AbstractSkill": "lexigram.ai.skills.base",
    "FunctionSkill": "lexigram.ai.skills.base",
    "ToolSkillAdapter": "lexigram.ai.skills.base",
    # --- Hooks ---
    "SkillExecutedHook": "lexigram.ai.skills.hooks",
    "SkillExecutionFailedHook": "lexigram.ai.skills.hooks",
    "SkillRegisteredHook": "lexigram.ai.skills.hooks",
    # --- Builtin ---
    "CodeExecutionSkill": "lexigram.ai.skills.builtin.code_execution",
    "DatabaseQuerySkill": "lexigram.ai.skills.builtin.database_query",
    "DateTimeSkill": "lexigram.ai.skills.builtin.datetime_skill",
    "FileReadSkill": "lexigram.ai.skills.builtin.file_operations",
    "FileWriteSkill": "lexigram.ai.skills.builtin.file_operations",
    "HTTPRequestSkill": "lexigram.ai.skills.builtin.http_request",
    "MathSkill": "lexigram.ai.skills.builtin.math_skill",
    "TextSummarizeSkill": "lexigram.ai.skills.builtin.text_processing",
    "TextTranslateSkill": "lexigram.ai.skills.builtin.text_processing",
    "WebSearchSkill": "lexigram.ai.skills.builtin.web_search",
    # --- Caching ---
    "SkillResultCache": "lexigram.ai.skills.caching.skill_cache",
    # --- Composition ---
    "SkillChain": "lexigram.ai.skills.composition.chain",
    "ParallelSkills": "lexigram.ai.skills.composition.parallel",
    "SkillPipeline": "lexigram.ai.skills.composition.pipeline",
    "SkillRouter": "lexigram.ai.skills.composition.router",
    # --- Config ---
    "SkillsConfig": "lexigram.ai.skills.config",
    # --- Decorators ---
    "skill": "lexigram.ai.skills.decorators",
    "skill_param": "lexigram.ai.skills.decorators",
    # --- DI ---
    "SkillsProvider": "lexigram.ai.skills.di.provider",
    # --- Discovery ---
    "MCPSkillBridge": "lexigram.ai.skills.discovery.mcp_bridge",
    "ModuleScanner": "lexigram.ai.skills.discovery.module_scanner",
    "SkillSourceScanner": "lexigram.ai.skills.discovery.skill_source_scanner",
    "SkillLoader": "lexigram.ai.skills.discovery.skill_loader",
    # --- Exceptions ---
    "SkillAlreadyRegisteredError": "lexigram.ai.skills.exceptions",
    "SkillExecutionError": "lexigram.ai.skills.exceptions",
    "SkillNotFoundError": "lexigram.ai.skills.exceptions",
    "SkillPermissionDeniedError": "lexigram.ai.skills.exceptions",
    "SkillRoutingError": "lexigram.ai.skills.exceptions",
    "SkillTimeoutError": "lexigram.ai.skills.exceptions",
    "SkillValidationError": "lexigram.ai.skills.exceptions",
    # --- Executor ---
    "SkillExecutor": "lexigram.ai.skills.executor",
    # --- Module ---
    "SkillsModule": "lexigram.ai.skills.module",
    # --- Permissions ---
    "PermissionChecker": "lexigram.ai.skills.permissions.permission_checker",
    # --- Registry ---
    "SkillRegistry": "lexigram.ai.skills.registry",
    # --- Validation ---
    "validate_params": "lexigram.ai.skills.validation.schema",
    "validate_non_empty_string": "lexigram.ai.skills.validation.validators",
    "validate_positive_int": "lexigram.ai.skills.validation.validators",
    "validate_range": "lexigram.ai.skills.validation.validators",
    # --- Contracts ---
    "SkillDefinition": "lexigram.contracts.ai.skills",
    "SkillError": "lexigram.contracts.ai.skills",
    "SkillExecutorProtocol": "lexigram.contracts.ai.skills",
    "SkillProtocol": "lexigram.contracts.ai.skills",
    "SkillRegistryProtocol": "lexigram.contracts.ai.skills",
    "SkillResult": "lexigram.contracts.ai.skills",
    # --- Events ---
    "SkillExecutedEvent": "lexigram.ai.skills.events",
}


def __getattr__(name: str) -> object:
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return sorted(set(__all__) | set(_LAZY_IMPORTS.keys()))


__all__ = list(_LAZY_IMPORTS.keys())

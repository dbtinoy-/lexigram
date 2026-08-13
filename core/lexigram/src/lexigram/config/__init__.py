"""Lexigram Config — Configuration loading, models, and sources.

This module uses lazy imports for all public symbols to keep
import overhead minimal.  Every name listed in _LAZY_IMPORTS
is available at package level:

    from lexigram.config import <Symbol>

or by accessing the attribute on the package:

    import lexigram.config as config
    config.<Symbol>
"""

from __future__ import annotations

__path__ = __import__("pkgutil").extend_path(__path__, __name__)

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from lexigram.config.base import BaseConfig
    from lexigram.config.constants import (
        DEFAULT_CONFIG_FILENAMES as DEFAULT_CONFIG_FILENAMES,
    )
    from lexigram.config.constants import (
        DEFAULT_ENV_VAR_PREFIX as DEFAULT_ENV_VAR_PREFIX,
    )
    from lexigram.config.constants import (
        DEFAULT_RELOAD_INTERVAL as DEFAULT_RELOAD_INTERVAL,
    )
    from lexigram.config.constants import (
        INSECURE_SECRET_VALUES as INSECURE_SECRET_VALUES,
    )
    from lexigram.config.constants import (
        SECRET_FIELD_PATTERNS as SECRET_FIELD_PATTERNS,
    )
    from lexigram.config.constants import (
        SUPPORTED_FORMATS as SUPPORTED_FORMATS,
    )
    from lexigram.config.exceptions import (
        ConfigReloadError as ConfigReloadError,
    )
    from lexigram.config.exceptions import (
        ConfigSectionNotFoundError as ConfigSectionNotFoundError,
    )
    from lexigram.config.exceptions import (
        ConfigSourceError as ConfigSourceError,
    )
    from lexigram.config.exceptions import (
        ConfigurationError as ConfigurationError,
    )
    from lexigram.config.lib.merge import deep_merge as deep_merge
    from lexigram.config.lib.merge import interpolate_env_vars as interpolate_env_vars
    from lexigram.config.lib.merge import interpolate_string as interpolate_string
    from lexigram.config.lib.registry import ConfigRegistry
    from lexigram.config.lib.sources import (
        CliConfigSource,
        ConfigLoader,
        ConfigSource,
        DirectoryConfigSource,
        DotEnvSource,
        EnvironmentConfigSource,
        FileConfigSource,
    )
    from lexigram.config.lib.validation import is_insecure_secret as is_insecure_secret
    from lexigram.config.lib.validation import (
        validate_all_configs as validate_all_configs,
    )
    from lexigram.config.lib.watcher import ConfigWatcher
    from lexigram.config.main import LexigramConfig
    from lexigram.config.protocols import ConfigSourceProtocol as ConfigSourceProtocol
    from lexigram.config.secrets import DEFAULT_MIN_LENGTHS as DEFAULT_MIN_LENGTHS
    from lexigram.config.secrets import (
        DEFAULT_PLACEHOLDER_VALUES as DEFAULT_PLACEHOLDER_VALUES,
    )
    from lexigram.config.secrets import SecretsPolicy as SecretsPolicy
    from lexigram.config.secrets import SecretsValidator as SecretsValidator
    from lexigram.config.secrets import (
        SecretsValidatorProtocol as SecretsValidatorProtocol,
    )
    from lexigram.config.secrets import SecretViolation as SecretViolation
    from lexigram.config.types import ConfigSourceType as ConfigSourceType
    from lexigram.contracts.core.config import ConfigIssue as ConfigIssue
    from lexigram.contracts.core.config import Environment as Environment
    from lexigram.contracts.exceptions import ConfigurationError
    from lexigram.logging.config import LoggingConfig, SamplingConfig

_LAZY_IMPORTS: dict[str, str] = {
    "BaseConfig": "lexigram.config.base",
    "CliConfigSource": "lexigram.config.lib.sources",
    "ConfigIssue": "lexigram.contracts.core.config",
    "ConfigLoader": "lexigram.config.lib.sources",
    "ConfigRegistry": "lexigram.config.lib.registry",
    "ConfigSource": "lexigram.config.lib.sources",
    "ConfigWatcher": "lexigram.config.lib.watcher",
    "ConfigurationError": "lexigram.contracts.exceptions",
    "DirectoryConfigSource": "lexigram.config.lib.sources",
    "DotEnvSource": "lexigram.config.lib.sources",
    "Environment": "lexigram.contracts.core.config",
    "EnvironmentConfigSource": "lexigram.config.lib.sources",
    "FileConfigSource": "lexigram.config.lib.sources",
    "LexigramConfig": "lexigram.config.main",
    "LoggingConfig": "lexigram.logging.config",
    "SamplingConfig": "lexigram.logging.config",
    "deep_merge": "lexigram.config.lib.merge",
    "interpolate_env_vars": "lexigram.config.lib.merge",
    "interpolate_string": "lexigram.config.lib.merge",
    "validate_all_configs": "lexigram.config.lib.validation",
    # secrets
    "DEFAULT_MIN_LENGTHS": "lexigram.config.secrets",
    "DEFAULT_PLACEHOLDER_VALUES": "lexigram.config.secrets",
    "SecretViolation": "lexigram.config.secrets",
    "SecretsPolicy": "lexigram.config.secrets",
    "SecretsValidator": "lexigram.config.secrets",
    "SecretsValidatorProtocol": "lexigram.config.secrets",
    # constants
    "DEFAULT_CONFIG_FILENAMES": "lexigram.config.constants",
    "DEFAULT_ENV_VAR_PREFIX": "lexigram.config.constants",
    "DEFAULT_RELOAD_INTERVAL": "lexigram.config.constants",
    "INSECURE_SECRET_VALUES": "lexigram.config.constants",
    "SECRET_FIELD_PATTERNS": "lexigram.config.constants",
    "SUPPORTED_FORMATS": "lexigram.config.constants",
    "is_insecure_secret": "lexigram.config.lib.validation",
    # exceptions
    "ConfigReloadError": "lexigram.config.exceptions",
    "ConfigSectionNotFoundError": "lexigram.config.exceptions",
    "ConfigSourceError": "lexigram.config.exceptions",
    # protocols
    "ConfigSourceProtocol": "lexigram.config.protocols",
    # types
    "ConfigSourceType": "lexigram.config.types",
    # provider
    "ConfigProvider": "lexigram.config.di.provider",
}


def __getattr__(name: str) -> Any:
    if name in _LAZY_IMPORTS:
        import importlib

        module = importlib.import_module(_LAZY_IMPORTS[name])
        value = getattr(module, name)
        globals()[name] = value
        return value
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


def __dir__() -> list[str]:
    return list(_LAZY_IMPORTS.keys())


__all__ = (
    "DEFAULT_CONFIG_FILENAMES",
    "DEFAULT_ENV_VAR_PREFIX",
    "DEFAULT_MIN_LENGTHS",
    "DEFAULT_PLACEHOLDER_VALUES",
    "DEFAULT_RELOAD_INTERVAL",
    "INSECURE_SECRET_VALUES",
    "SECRET_FIELD_PATTERNS",
    "SUPPORTED_FORMATS",
    "BaseConfig",
    "CliConfigSource",
    "ConfigIssue",
    "ConfigLoader",
    "ConfigRegistry",
    "ConfigReloadError",
    "ConfigSectionNotFoundError",
    "ConfigSource",
    "ConfigSourceError",
    "ConfigSourceProtocol",
    "ConfigSourceType",
    "ConfigWatcher",
    "ConfigurationError",
    "DirectoryConfigSource",
    "DotEnvSource",
    "Environment",
    "EnvironmentConfigSource",
    "FileConfigSource",
    "LexigramConfig",
    "LoggingConfig",
    "SamplingConfig",
    "SecretViolation",
    "SecretsPolicy",
    "SecretsValidator",
    "SecretsValidatorProtocol",
    "deep_merge",
    "interpolate_env_vars",
    "interpolate_string",
    "is_insecure_secret",
    "validate_all_configs",
)
__version__ = "0.1.0"

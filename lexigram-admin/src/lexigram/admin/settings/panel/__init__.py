"""Config panel UI subsystem for the Configuration Center.

This package contains all UI-layer components for the admin configuration
panel: node definitions, spec registry, category types, layout, dashboard UI,
controller, and the built-in spec registrations.

Public exports for the settings panel. Spec bindings and models are imported
by spec modules, not re-exported here.
"""

from __future__ import annotations

from lexigram.admin.settings.panel.branding_spec import BrandingSpec
from lexigram.admin.settings.panel.branding_spec import (
    register_spec as register_branding_spec,
)
from lexigram.admin.settings.panel.cache_spec import CacheSpec
from lexigram.admin.settings.panel.cache_spec import (
    register_spec as register_cache_spec,
)
from lexigram.admin.settings.panel.features_spec import FeaturesSpec
from lexigram.admin.settings.panel.features_spec import (
    register_spec as register_features_spec,
)
from lexigram.admin.settings.panel.i18n_spec import I18nSpec
from lexigram.admin.settings.panel.i18n_spec import register_spec as register_i18n_spec
from lexigram.admin.settings.panel.layout import ConfigLayout
from lexigram.admin.settings.panel.nodes import (
    AbstractConfigNode,
    BooleanNode,
    ColorNode,
    ConfigSpec,
    ConfigSpecMeta,
    EnumNode,
    IntNode,
    PydanticConfigSpec,
    SecretNode,
    StringNode,
)
from lexigram.admin.settings.panel.profiler_spec import ProfilerSpec
from lexigram.admin.settings.panel.profiler_spec import (
    register_spec as register_profiler_spec,
)
from lexigram.admin.settings.panel.rate_limit_spec import RateLimitSpec
from lexigram.admin.settings.panel.rate_limit_spec import (
    register_spec as register_rate_limit_spec,
)
from lexigram.admin.settings.panel.rbac_spec import RBACSpec
from lexigram.admin.settings.panel.rbac_spec import register_spec as register_rbac_spec
from lexigram.admin.settings.panel.registry import (
    ConfigRegistry,
    EnvStore,
    MemoryStore,
    StoreBase,
)
from lexigram.admin.settings.panel.security_spec import SecuritySpec
from lexigram.admin.settings.panel.security_spec import (
    register_spec as register_security_spec,
)
from lexigram.admin.settings.panel.types import ConfigCategory
from lexigram.admin.settings.panel.ui import ConfigDashboardUI

__all__ = [
    "AbstractConfigNode",
    "BooleanNode",
    "BrandingSpec",
    "CacheSpec",
    "ColorNode",
    "ConfigCategory",
    "ConfigDashboardUI",
    "ConfigLayout",
    "ConfigRegistry",
    "ConfigSpec",
    "ConfigSpecMeta",
    "EnumNode",
    "EnvStore",
    "FeaturesSpec",
    "I18nSpec",
    "IntNode",
    "MemoryStore",
    "ProfilerSpec",
    "PydanticConfigSpec",
    "RBACSpec",
    "RateLimitSpec",
    "SecretNode",
    "SecuritySpec",
    "StoreBase",
    "StringNode",
    "register_branding_spec",
    "register_cache_spec",
    "register_features_spec",
    "register_i18n_spec",
    "register_profiler_spec",
    "register_rate_limit_spec",
    "register_rbac_spec",
    "register_security_spec",
]

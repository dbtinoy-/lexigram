"""Model access policy — allowlist/denylist glob evaluation.

Pure policy evaluation for per-user model restrictions.  A
user-specific entry takes precedence over the ``"*"`` wildcard entry;
with no applicable entry, access is allowed.
"""

from __future__ import annotations

import fnmatch
from typing import TYPE_CHECKING

from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.ai.governance.config import GovernanceConfig

logger = get_logger(__name__)

__all__ = ["model_access_allowed"]


def model_access_allowed(
    config: GovernanceConfig, user_id: str | None, model: str
) -> bool:
    """Evaluate *config* allow/deny glob lists for (*user_id*, *model*).

    Logic:
    1. If ``model_allowlist`` has an entry for the effective key, the model
       must match at least one pattern in the allowlist.
    2. If ``model_denylist`` has an entry for the effective key, the model
       must not match any pattern in the denylist.
    3. When no entry exists for the key, access is allowed.

    Args:
        config: Governance policy configuration.
        user_id: User identifier, or ``None`` for anonymous / global.
        model: Model name to check.

    Returns:
        True if access is permitted, False if denied.
    """
    key = user_id or "global"

    allowlist = config.model_allowlist.get(key) or config.model_allowlist.get("*")
    if allowlist:
        if not any(fnmatch.fnmatch(model, pattern) for pattern in allowlist):
            logger.warning(
                "governance_model_not_in_allowlist",
                user_id=user_id,
                model=model,
            )
            return False

    denylist = config.model_denylist.get(key) or config.model_denylist.get("*")
    if denylist:
        if any(fnmatch.fnmatch(model, pattern) for pattern in denylist):
            logger.warning(
                "governance_model_in_denylist",
                user_id=user_id,
                model=model,
            )
            return False

    return True

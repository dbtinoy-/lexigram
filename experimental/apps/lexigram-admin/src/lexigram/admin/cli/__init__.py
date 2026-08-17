"""Admin package CLI contributor and generators.

CLI is tooling, not a runtime API. Use the `lexigram-admin` console script.
"""

from __future__ import annotations

import os
import warnings

if not __name__.endswith(".__main__") and "_LEX_ADMIN_CLI_OK" not in os.environ:
    warnings.warn(
        "lexigram.admin.cli is tooling, not a runtime API. "
        "Use the `lexigram-admin` console script instead.",
        ImportWarning,
        stacklevel=2,
    )

from lexigram.admin.cli.contributor import AdminCliContributor
from lexigram.admin.cli.generators.admin_action import AdminActionGenerator
from lexigram.admin.cli.generators.admin_resource import AdminResourceGenerator

__all__ = ["AdminActionGenerator", "AdminCliContributor", "AdminResourceGenerator"]

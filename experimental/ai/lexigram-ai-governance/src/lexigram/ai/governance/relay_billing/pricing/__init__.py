"""Decimal price calculation and restricted expression evaluation.

Computes per-dimension relay charges from normalized ``RelayUsage`` and
configured price snapshots.  Price expressions are ported from the
relaykit billing conventions and evaluated by a small allow-listed
parser: numeric literals, named usage dimensions, ``+ - * /``, ``min``,
``max``, and parentheses.  Attribute access, arbitrary calls,
exponentiation, assignment, imports, and unbounded recursion are
rejected.  All arithmetic uses non-negative ``Decimal`` with explicit
per-dimension rounding; every safety violation returns a
``RelayBillingError`` instead of clamping silently.

This package re-exports the original module surface so the historical
import path (``lexigram.ai.governance.relay_billing.pricing``) remains
valid:

- :mod:`.parser` — restricted expression tokenizer/parser/evaluator.
- :mod:`.engine` — price snapshots and :class:`RelayPricingEngine`.
- :mod:`.simple_estimator` — :class:`SimpleCostEstimator`.
"""

from __future__ import annotations

from lexigram.ai.governance.relay_billing.pricing.engine import (
    BREAKDOWN_FIELDS as BREAKDOWN_FIELDS,
)
from lexigram.ai.governance.relay_billing.pricing.engine import (
    DEFAULT_MAX_CHARGE as DEFAULT_MAX_CHARGE,
)
from lexigram.ai.governance.relay_billing.pricing.engine import (
    PriceSnapshot as PriceSnapshot,
)
from lexigram.ai.governance.relay_billing.pricing.engine import (
    RelayPricingEngine as RelayPricingEngine,
)
from lexigram.ai.governance.relay_billing.pricing.parser import (
    DEFAULT_MAX_TOKENS as DEFAULT_MAX_TOKENS,
)
from lexigram.ai.governance.relay_billing.pricing.parser import (
    DEFAULT_SCALE as DEFAULT_SCALE,
)
from lexigram.ai.governance.relay_billing.pricing.parser import (
    evaluate_expression as evaluate_expression,
)
from lexigram.ai.governance.relay_billing.pricing.simple_estimator import (
    SimpleCostEstimator as SimpleCostEstimator,
)

__all__ = [
    "BREAKDOWN_FIELDS",
    "DEFAULT_MAX_CHARGE",
    "DEFAULT_MAX_TOKENS",
    "DEFAULT_SCALE",
    "PriceSnapshot",
    "RelayPricingEngine",
    "SimpleCostEstimator",
    "evaluate_expression",
]

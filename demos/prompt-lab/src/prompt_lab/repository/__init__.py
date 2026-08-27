"""Data access, fixtures, and scripted stores.

Re-exports key symbols so callers can import from the package root:

    from prompt_lab.repository import TEMPLATES, CASES, VARIANT_LABELS
"""

from prompt_lab.repository.cases import CASES, CRITERIA, Case
from prompt_lab.repository.responders import RESPONDERS
from prompt_lab.repository.templates import TEMPLATES, VARIANT_LABELS

__all__ = [
    "CASES",
    "CRITERIA",
    "RESPONDERS",
    "TEMPLATES",
    "VARIANT_LABELS",
    "Case",
]

"""Relay gateway package namespace for the Lexigram AI subsystem.

This package is split across lexigram-ai-relay (conversion engine) and
lexigram-ai-relay-gateway (gateway); see the respective submodules.
"""

from __future__ import annotations

from pkgutil import extend_path

__path__ = extend_path(__path__, __name__)

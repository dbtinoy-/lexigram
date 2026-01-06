from __future__ import annotations

from lexigram.app.base import Application
from lexigram.app.standard import StandardModule
from lexigram.config.main import LexigramConfig
from lexigram.contracts.core.serialization import JsonSerializerProtocol


def test_standard_module_re_exports_core_exports() -> None:
    """StandardModule should expose the core exports it extends."""
    dynamic_module = StandardModule.configure()

    assert Application in dynamic_module.exports
    assert LexigramConfig in dynamic_module.exports
    assert JsonSerializerProtocol in dynamic_module.exports

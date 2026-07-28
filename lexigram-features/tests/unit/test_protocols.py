"""Tests for feature flags protocol re-exports."""

from __future__ import annotations

import pytest


class TestProtocolReExports:
    """Tests that protocols are correctly re-exported."""

    def test_flag_provider_protocol_is_importable(self) -> None:
        """FlagProviderProtocol is importable from lexigram.features.protocols."""
        from lexigram.features.protocols import FlagProviderProtocol

        assert FlagProviderProtocol is not None

    def test_flag_manager_protocol_is_importable(self) -> None:
        """FlagManagerProtocol is importable from lexigram.features.protocols."""
        from lexigram.features.protocols import FlagManagerProtocol

        assert FlagManagerProtocol is not None

    def test_mutable_flag_provider_protocol_is_importable(self) -> None:
        """MutableFlagProviderProtocol is importable from lexigram.features.protocols."""
        from lexigram.features.protocols import MutableFlagProviderProtocol

        assert MutableFlagProviderProtocol is not None

    def test_re_exports_match_contracts(self) -> None:
        """Re-exports point to the same objects as contracts originals."""
        from lexigram.contracts.feature_flags.protocols import (
            FlagManagerProtocol as ContractsFlagManagerProtocol,
        )
        from lexigram.contracts.feature_flags.protocols import (
            FlagProviderProtocol as ContractsFlagProviderProtocol,
        )
        from lexigram.contracts.feature_flags.protocols import (
            MutableFlagProviderProtocol as ContractsMutableFlagProviderProtocol,
        )
        from lexigram.features.protocols import FlagManagerProtocol
        from lexigram.features.protocols import FlagProviderProtocol
        from lexigram.features.protocols import MutableFlagProviderProtocol

        assert FlagProviderProtocol is ContractsFlagProviderProtocol
        assert FlagManagerProtocol is ContractsFlagManagerProtocol
        assert MutableFlagProviderProtocol is ContractsMutableFlagProviderProtocol

    def test_all_exports_are_defined(self) -> None:
        """__all__ contains the expected protocol names."""
        from lexigram.features import protocols

        assert "FlagProviderProtocol" in protocols.__all__
        assert "FlagManagerProtocol" in protocols.__all__
        assert "MutableFlagProviderProtocol" in protocols.__all__

"""Unit tests for UI module."""

import pytest
from unittest.mock import MagicMock, patch

from lexigram.di.module import DynamicModule
from lexigram.ui import UIModule
from lexigram.ui.config import UIConfig


class TestUIModule:
    """Test UIModule functionality."""

    def test_module_creation(self):
        """Test module can be created."""
        module = UIModule.configure()
        assert module is not None

    def test_module_with_config(self):
        """Test module creation with config."""
        config = UIConfig(
            theme="dark",
            enable_sse=True,
        )
        module = UIModule.configure(config)
        assert module is not None

    def test_module_configure_returns_dynamic_module(self):
        """configure() returns a properly configured DynamicModule."""
        module = UIModule.configure()
        assert isinstance(module, DynamicModule)
        assert len(module.providers) > 0

    def test_module_configure_with_config_returns_dynamic_module(self):
        """configure() accepts optional UIConfig and still returns a DynamicModule."""
        config = UIConfig(theme="dark")
        module = UIModule.configure(config)
        assert isinstance(module, DynamicModule)


class TestUIConfig:
    """Test UI configuration."""

    def test_config_defaults(self):
        """Test default configuration values."""
        config = UIConfig()
        assert config.theme == "light"
        assert config.enable_sse is False

    def test_config_with_custom_values(self):
        """Test configuration with custom values."""
        config = UIConfig(
            theme="dark",
            enable_sse=True,
            enable_realtime=True,
        )
        assert config.theme == "dark"
        assert config.enable_sse is True
        assert config.enable_realtime is True


class TestUIComponent:
    """Test UI component base."""

    def test_component_base_import(self):
        """Verify Component base is importable."""
        from lexigram.ui.core.base import Component
        assert Component is not None

    def test_component_render_method(self):
        """Verify Component has render method."""
        from lexigram.ui.core.base import Component
        assert hasattr(Component, 'render')


class TestUIContext:
    """Test UI context."""

    def test_context_creation(self):
        """Test context can be created."""
        from lexigram.ui.core.context import UIContext
        ctx = UIContext()
        assert ctx is not None

    def test_context_with_theme(self):
        """Test context with theme."""
        from lexigram.ui.core.context import UIContext
        ctx = UIContext(theme="dark")
        assert ctx.theme == "dark"

    def test_context_immutable(self):
        """Test context is immutable."""
        from lexigram.ui.core.context import UIContext
        ctx = UIContext(theme="light")
        with pytest.raises(AttributeError):
            ctx.theme = "dark"


class TestUIAtoms:
    """Test UI atom components."""

    def test_button_import(self):
        """Verify Button is importable."""
        from lexigram.ui.atoms.button import Button
        assert Button is not None

    def test_badge_import(self):
        """Verify Badge is importable."""
        from lexigram.ui.atoms.badge import Badge
        assert Badge is not None

    def test_input_import(self):
        """Verify Input is importable."""
        from lexigram.ui.atoms.inputs.text import Input
        assert Input is not None


class TestUIMolecules:
    """Test UI molecule components."""

    def test_alert_import(self):
        """Verify Alert is importable."""
        from lexigram.ui.molecules.alert import Alert
        assert Alert is not None

    def test_card_import(self):
        """Verify Card is importable."""
        from lexigram.ui.molecules.card import Card
        assert Card is not None

    def test_modal_import(self):
        """Verify Modal is importable."""
        from lexigram.ui.molecules.modal import Modal
        assert Modal is not None


class TestUIOrganisms:
    """Test UI organism components."""

    def test_form_import(self):
        """Verify Form is importable."""
        from lexigram.ui.organisms.forms import Form
        assert Form is not None

    def test_chart_import(self):
        """Verify Chart components are importable."""
        from lexigram.ui.charts import BarChart, ChartConfig, ChartDataPoint, ChartType, LineChart, PieChart
        assert BarChart is not None
        assert ChartType is not None
        assert ChartDataPoint is not None
        assert ChartConfig is not None

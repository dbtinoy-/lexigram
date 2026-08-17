"""Structural layout test for lexigram-admin Task 4 normalization.

Asserts the canonical layout after:
- utils/ → lib/
- protocols.py canonical surface (interfaces/ dissolved)
- events.py root module (events/ package dissolved)
- monitoring/ kept, monitor/ removed
"""

from __future__ import annotations

from pathlib import Path

import pytest

# Root of the admin source tree
# __file__ is tests/unit/test_package_structure_p1.py
# parents[0] = tests/unit/, parents[1] = tests/, parents[2] = project root
_ADMIN_SRC = Path(__file__).parents[2] / "src" / "lexigram" / "admin"


class TestLibLayout:
    """utils/ renamed to lib/."""

    def test_lib_dir_exists(self) -> None:
        assert (_ADMIN_SRC / "lib").is_dir(), "lib/ must exist"

    def test_utils_dir_removed(self) -> None:
        assert not (_ADMIN_SRC / "utils").exists(), "utils/ must not exist"


class TestProtocolsLayout:
    """Protocols promoted to lexigram-contracts."""

    def test_protocols_py_removed(self) -> None:
        # protocols.py was the backward-compat shim. All imports migrated to contracts.
        assert not (_ADMIN_SRC / "protocols.py").exists(), "protocols.py must not exist"

    def test_interfaces_dir_removed(self) -> None:
        assert not (_ADMIN_SRC / "interfaces").exists(), "interfaces/ must not exist"


class TestEventsLayout:
    """events/ package is the canonical surface via ``__init__.py``."""

    def test_root_events_py_exists(self) -> None:
        assert (_ADMIN_SRC / "events" / "__init__.py").is_file(), (
            "events/__init__.py must exist"
        )

    def test_domain_events_py_removed(self) -> None:
        assert not (_ADMIN_SRC / "domain" / "events.py").exists(), (
            "domain/events.py must not exist"
        )

    def test_events_subpackage_events_py_removed(self) -> None:
        assert not (_ADMIN_SRC / "events" / "events.py").exists(), (
            "events/events.py must not exist"
        )

    def test_events_subpackage_is_package(self) -> None:
        assert (_ADMIN_SRC / "events").is_dir(), "events/ directory must exist"

    def test_handlers_module_exists(self) -> None:
        assert (_ADMIN_SRC / "handlers" / "admin_command_handlers.py").is_file(), (
            "handlers/admin_command_handlers.py must exist"
        )

    def test_cqrs_commands_module_exists(self) -> None:
        assert (_ADMIN_SRC / "cqrs" / "commands.py").is_file(), (
            "cqrs/commands.py must exist"
        )


class TestMonitoringLayout:
    """monitoring/ removed — all monitoring moved to lexigram-monitor."""

    def test_monitoring_dir_removed(self) -> None:
        assert not (_ADMIN_SRC / "monitoring").exists(), "monitoring/ must not exist"

    def test_monitor_dir_removed(self) -> None:
        assert not (_ADMIN_SRC / "monitor").exists(), "monitor/ must not exist"


class TestExportServiceLayout:
    """services/export/ uses adapters/ sub-directory; backends/ must not exist."""

    def test_export_adapters_dir_exists(self) -> None:
        assert (_ADMIN_SRC / "services" / "export" / "adapters").is_dir(), (
            "services/export/adapters/ must exist"
        )

    def test_export_backends_dir_removed(self) -> None:
        assert not (_ADMIN_SRC / "services" / "export" / "backends").exists(), (
            "services/export/backends/ must not exist"
        )


class TestDataLayout:
    """data/data_source.py is the canonical destination for dissolved interfaces helpers."""

    def test_data_source_py_exists(self) -> None:
        assert (_ADMIN_SRC / "data" / "data_source.py").is_file(), (
            "data/data_source.py must exist"
        )

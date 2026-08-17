"""Layout config DI registration test."""
from __future__ import annotations

import pytest


@pytest.mark.asyncio
async def test_ui_provider_registers_layout_configs() -> None:
    """All layout config dataclasses must be resolvable from the container."""
    import inspect

    from lexigram.di.container import Container
    from lexigram.ui.di.provider import UIProvider

    container = Container()
    provider = UIProvider()
    await provider.register(container)
    await provider.boot(container)

    # Import config types through the public API
    from lexigram.ui.config import (
        BaseLayoutConfig,
        FooterConfig,
        HeadConfig,
        HTMLDocumentConfig,
        ToastConfig,
    )

    for cfg_type in [HTMLDocumentConfig, BaseLayoutConfig, HeadConfig, FooterConfig, ToastConfig]:
        resolved = await container.resolve(cfg_type)
        assert resolved is not None, f"Container could not resolve {cfg_type.__name__}"
        assert isinstance(resolved, cfg_type), f"Resolved {type(resolved)} but expected {cfg_type.__name__}"

    await provider.shutdown()

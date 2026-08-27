# MFA Configuration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a first-class `MFAConfig` section to `AuthConfig` so MFA parameters (TOTP digits, interval, window, backup codes, issuer, max attempts) are configurable via `application.yaml` instead of hardcoded in constants and demo code.

**Architecture:** Introduce `TOTPConfig`, `BackupCodeConfig`, `MFAConfig` dataclasses in `lexigram.auth.config`, add `mfa` field to `AuthConfig`, update `MFAManager` to accept and use config, wire `MFAProvider` as a sub-provider in `AuthBundleProvider`, and update the auth-mfa demo to consume the new config section.

**Tech Stack:** Python 3.13, stdlib dataclasses (via `BaseConfig`/`DomainModel`), Lexigram DI container, Lexigram config system.

**Spec:** This plan is self-authored from codebase analysis. No external spec file.

## Global Constraints

- All changes must pass `ruff check`, `ruff format --check`, and existing tests.
- `AuthConfig` uses `extra="ignore"` — new fields with defaults are backward-compatible.
- `MFAConfig` must follow the same `@dataclass(init=False)` + `BaseConfig` pattern as `PasswordConfig`, `RBACConfig`, etc.
- Environment variable override: `LEX_AUTH__MFA__TOTP__DIGITS=8` etc. (follows existing `LEX_AUTH__` prefix + `__` nested delimiter convention).
- MFA state remains in `user.profile['mfa']` — no schema changes.
- Sub-providers (`MFAProvider`) do NOT declare `config_key`/`config_model` — they receive config via constructor (same pattern as `TokenProvider`, `SessionProvider`).

## Config System How-It-Works

The config flow for this change:

1. `application.yaml` has `auth.mfa.totp.digits: 8` etc.
2. Orchestrator loads yaml, calls `lex_config.get_section("auth", AuthConfig)`
3. `DomainModel._coerce_value` sees `mfa: MFAConfig` field, val is dict → calls `MFAConfig(**val)`
4. Nested: `totp` dict → `TOTPConfig(**val)`, `backup` dict → `BackupCodeConfig(**val)`
5. `AuthBundleProvider` receives `AuthConfig` (with populated `mfa` field) via `config_key`/`config_model`
6. `_compose_sub_providers()` passes `config` to each sub-provider constructor
7. `MFAProvider.register()` passes `config.mfa` to `MFAManager` factory

## File Map

| File | Action | Responsibility |
|------|--------|----------------|
| `packages/lexigram-auth/src/lexigram/auth/constants.py` | Modify | Add `DEFAULT_MFA_ISSUER`, `DEFAULT_BACKUP_CODE_COUNT`, `DEFAULT_BACKUP_CODE_LENGTH`, `DEFAULT_MAX_CHALLENGE_ATTEMPTS` |
| `packages/lexigram-auth/src/lexigram/auth/config.py` | Modify | Add `TOTPConfig`, `BackupCodeConfig`, `MFAConfig` dataclasses; add `mfa` field to `AuthConfig` |
| `packages/lexigram-auth/src/lexigram/auth/mfa/manager.py` | Modify | Accept `MFAConfig`, use config values in `enable_totp()`, `verify_totp()`, `generate_backup_codes()` |
| `packages/lexigram-auth/src/lexigram/auth/di/sub_providers/mfa_provider.py` | Modify | Accept `AuthConfig`, register `MFAManager` with config in `register()` (sub-provider pattern) |
| `packages/lexigram-auth/src/lexigram/auth/di/bundle_provider.py` | Modify | Import `MFAProvider`, add to `_compose_sub_providers()` |
| `demos/auth-mfa/application.yaml` | Modify | Add `auth.mfa` section with TOTP/backup/issuer/limits config |
| `demos/auth-mfa/src/mfa_console/controllers/api.py` | Modify | Accept `AuthConfig`, read `max_challenge_attempts` from config |
| `demos/auth-mfa/src/mfa_console/di/provider.py` | Modify | Remove redundant `build_mfa` factory (framework `MFAProvider` handles it); pass `AuthConfig` to controller factory |
| `packages/lexigram-auth/tests/unit/test_mfa_config.py` | Create | Unit tests for `MFAConfig` defaults, env override, validation |
| `packages/lexigram-auth/tests/unit/test_mfa_manager_config.py` | Create | Unit tests for `MFAManager` using config values |

---

## Task 1: Add MFA constants to `constants.py`

**Files:**
- Modify: `packages/lexigram-auth/src/lexigram/auth/constants.py`

**Interfaces:**
- Consumes: (none — standalone constants)
- Produces: `DEFAULT_MFA_ISSUER`, `DEFAULT_BACKUP_CODE_COUNT`, `DEFAULT_BACKUP_CODE_LENGTH`, `DEFAULT_MAX_CHALLENGE_ATTEMPTS`

- [ ] **Step 1: Add new MFA constants**

After the existing MFA defaults block (after `DEFAULT_TOTP_VALID_WINDOW`), add:

```python
DEFAULT_MFA_ISSUER: str = "lexigram"
DEFAULT_BACKUP_CODE_COUNT: int = 10
DEFAULT_BACKUP_CODE_LENGTH: int = 8
DEFAULT_MAX_CHALLENGE_ATTEMPTS: int = 3
```

- [ ] **Step 2: Update `__all__`**

Add the four new names to `__all__` (alphabetical order within the MFA section).

- [ ] **Step 3: Run existing tests to verify no breakage**

Run: `uv run pytest packages/lexigram-auth/tests/unit/test_auth_constants.py -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add packages/lexigram-auth/src/lexigram/auth/constants.py
git commit -m "✨ feat(auth): add MFA config constants (issuer, backup codes, max attempts)"
```

---

## Task 2: Add `MFAConfig` dataclass to `config.py`

**Files:**
- Modify: `packages/lexigram-auth/src/lexigram/auth/config.py`
- Create: `packages/lexigram-auth/tests/unit/test_mfa_config.py`

**Interfaces:**
- Consumes: constants from Task 1 (`DEFAULT_TOTP_DIGITS`, `DEFAULT_TOTP_INTERVAL`, `DEFAULT_TOTP_VALID_WINDOW`, `DEFAULT_MFA_ISSUER`, `DEFAULT_BACKUP_CODE_COUNT`, `DEFAULT_BACKUP_CODE_LENGTH`, `DEFAULT_MAX_CHALLENGE_ATTEMPTS`)
- Produces: `TOTPConfig`, `BackupCodeConfig`, `MFAConfig` classes; `mfa` field on `AuthConfig`

- [ ] **Step 1: Write failing test for MFAConfig defaults**

Create `packages/lexigram-auth/tests/unit/test_mfa_config.py`:

```python
"""Tests for MFA configuration models."""
from __future__ import annotations

from lexigram.auth.config import AuthConfig, BackupCodeConfig, MFAConfig, TOTPConfig, JWTConfig


def test_mfa_config_defaults() -> None:
    cfg = MFAConfig()
    assert cfg.enabled is True
    assert cfg.totp.digits == 6
    assert cfg.totp.interval == 30
    assert cfg.totp.valid_window == 1
    assert cfg.backup.issuer == "lexigram"
    assert cfg.backup.count == 10
    assert cfg.backup.length == 8
    assert cfg.max_challenge_attempts == 3


def test_auth_config_mfa_defaults() -> None:
    cfg = AuthConfig()
    assert cfg.mfa is not None
    assert cfg.mfa.enabled is True
    assert cfg.mfa.totp.digits == 6


def test_mfa_config_from_dict() -> None:
    data = {
        "enabled": True,
        "totp": {"digits": 8, "interval": 60, "valid_window": 2},
        "backup": {"issuer": "my-app", "count": 5, "length": 10},
        "max_challenge_attempts": 5,
    }
    cfg = MFAConfig(**data)
    assert cfg.totp.digits == 8
    assert cfg.totp.interval == 60
    assert cfg.backup.issuer == "my-app"
    assert cfg.backup.count == 5
    assert cfg.max_challenge_attempts == 5


def test_mfa_config_partial_dict() -> None:
    """Partial dict only overrides specified fields; rest use defaults."""
    cfg = MFAConfig(totp={"digits": 8})
    assert cfg.totp.digits == 8
    assert cfg.totp.interval == 30  # default
    assert cfg.backup.issuer == "lexigram"  # default
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/lexigram-auth/tests/unit/test_mfa_config.py -v`
Expected: FAIL with `ImportError: cannot import name 'MFAConfig'`

- [ ] **Step 3: Add `TOTPConfig`, `BackupCodeConfig`, `MFAConfig` to config.py**

In `packages/lexigram-auth/src/lexigram/auth/config.py`, after `PasswordConfig` (around line 276) and before `AuthMiddlewareConfig`, add:

```python
@dataclass(init=False)
class TOTPConfig(BaseConfig):
    """TOTP (RFC 6238) configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    digits: int = Field(
        default=const.DEFAULT_TOTP_DIGITS,
        description="Number of digits in the TOTP code",
    )
    interval: int = Field(
        default=const.DEFAULT_TOTP_INTERVAL,
        description="Time-step period in seconds",
    )
    valid_window: int = Field(
        default=const.DEFAULT_TOTP_VALID_WINDOW,
        description="Number of time steps to check before/after current",
    )


@dataclass(init=False)
class BackupCodeConfig(BaseConfig):
    """Backup code generation configuration."""

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    issuer: str = Field(
        default=const.DEFAULT_MFA_ISSUER,
        description="Issuer label shown in authenticator apps",
    )
    count: int = Field(
        default=const.DEFAULT_BACKUP_CODE_COUNT,
        description="Number of backup codes to generate",
    )
    length: int = Field(
        default=const.DEFAULT_BACKUP_CODE_LENGTH,
        description="Length of each backup code",
    )


@dataclass(init=False)
class MFAConfig(BaseConfig):
    """Multi-factor authentication configuration.

    Controls TOTP settings, backup code generation, and challenge
    attempt limits.  MFA state is stored in the user profile
    (``user.profile['mfa']``) — no separate MFA table is required.
    """

    model_config: ClassVar[ConfigDict] = ConfigDict(extra="ignore")

    enabled: bool = Field(
        default=True,
        description="Enable MFA subsystem globally",
    )
    totp: TOTPConfig = Field(default_factory=TOTPConfig, description="TOTP settings")
    backup: BackupCodeConfig = Field(
        default_factory=BackupCodeConfig,
        description="Backup code settings",
    )
    max_challenge_attempts: int = Field(
        default=const.DEFAULT_MAX_CHALLENGE_ATTEMPTS,
        description="Max failed MFA challenge attempts before session is revoked",
    )
```

- [ ] **Step 4: Add `mfa` field to `AuthConfig`**

In `AuthConfig` (after the `users` field or `relay_verification` field), add:

```python
    mfa: MFAConfig = Field(
        default_factory=MFAConfig,
        description="Multi-factor authentication configuration",
    )
```

- [ ] **Step 5: Update `__all__` in config.py**

Add `MFAConfig`, `TOTPConfig`, `BackupCodeConfig` to the `__all__` list.

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest packages/lexigram-auth/tests/unit/test_mfa_config.py -v`
Expected: PASS

- [ ] **Step 7: Run full auth test suite to verify no breakage**

Run: `uv run pytest packages/lexigram-auth/tests/ -v --tb=short 2>&1 | tail -20`
Expected: All existing tests pass (MFAConfig has defaults, so AuthConfig without mfa: section still works)

- [ ] **Step 8: Commit**

```bash
git add packages/lexigram-auth/src/lexigram/auth/config.py packages/lexigram-auth/tests/unit/test_mfa_config.py
git commit -m "✨ feat(auth): add MFAConfig dataclass with TOTP, backup codes, and challenge limits"
```

---

## Task 3: Update `MFAManager` to accept and use `MFAConfig`

**Files:**
- Modify: `packages/lexigram-auth/src/lexigram/auth/mfa/manager.py`
- Create: `packages/lexigram-auth/tests/unit/test_mfa_manager_config.py`

**Interfaces:**
- Consumes: `MFAConfig` from Task 2
- Produces: `MFAManager` constructor now accepts `config: MFAConfig | None`; `enable_totp()` uses `config.backup.issuer`; `verify_totp()` uses `config.totp.valid_window`; `generate_backup_codes()` uses `config.backup.count` and `config.backup.length`

- [ ] **Step 1: Write failing test for MFAManager config usage**

Create `packages/lexigram-auth/tests/unit/test_mfa_manager_config.py`:

```python
"""Tests for MFAManager using MFAConfig values."""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

from lexigram.auth.config import BackupCodeConfig, MFAConfig, TOTPConfig
from lexigram.auth.mfa.manager import MFAManager


def _mock_user_store() -> MagicMock:
    store = MagicMock()
    store.get_user_by_id = AsyncMock(return_value=None)
    store.update_user = AsyncMock()
    return store


def test_mfa_manager_default_config() -> None:
    manager = MFAManager(user_store=_mock_user_store())
    assert manager.config is not None
    assert manager.config.totp.digits == 6
    assert manager.config.totp.interval == 30
    assert manager.config.totp.valid_window == 1
    assert manager.config.backup.issuer == "lexigram"
    assert manager.config.backup.count == 10
    assert manager.config.backup.length == 8


def test_mfa_manager_custom_config() -> None:
    cfg = MFAConfig(
        totp=TOTPConfig(digits=8, interval=60, valid_window=2),
        backup=BackupCodeConfig(issuer="my-app", count=5, length=10),
        max_challenge_attempts=5,
    )
    manager = MFAManager(user_store=_mock_user_store(), config=cfg)
    assert manager.config.totp.digits == 8
    assert manager.config.backup.issuer == "my-app"
    assert manager.config.backup.count == 5
```

- [ ] **Step 2: Run test to verify it fails**

Run: `uv run pytest packages/lexigram-auth/tests/unit/test_mfa_manager_config.py -v`
Expected: FAIL with `TypeError: MFAManager.__init__() got an unexpected keyword argument 'config'`

- [ ] **Step 3: Update `MFAManager.__init__` to accept config**

In `packages/lexigram-auth/src/lexigram/auth/mfa/manager.py`:

```python
from lexigram.auth.config import MFAConfig

@inject
class MFAManager:
    def __init__(
        self,
        user_store: UserStoreProtocol,
        config: MFAConfig | None = None,
    ) -> None:
        self.user_store = user_store
        self.config = config or MFAConfig()
```

- [ ] **Step 4: Update `enable_totp()` to use config**

Replace the hardcoded `issuer` default and pass config values to `generate_backup_codes`:

```python
    async def enable_totp(
        self,
        user_id: str,
        issuer: str | None = None,
    ) -> tuple[str, str, list[str]]:
        ...
        if issuer is None:
            issuer = self.config.backup.issuer
        ...
        backup_codes = generate_backup_codes(
            count=self.config.backup.count,
            length=self.config.backup.length,
        )
```

- [ ] **Step 5: Update `verify_totp()` to use config window**

```python
    async def verify_totp(self, user_id: str, code: str) -> bool:
        ...
        if secret and verify_totp(
            secret, code, window=self.config.totp.valid_window
        ):
            return True
```

- [ ] **Step 6: Run tests to verify they pass**

Run: `uv run pytest packages/lexigram-auth/tests/unit/test_mfa_manager_config.py -v`
Expected: PASS

- [ ] **Step 7: Run full auth test suite**

Run: `uv run pytest packages/lexigram-auth/tests/ -v --tb=short 2>&1 | tail -20`
Expected: All tests pass

- [ ] **Step 8: Commit**

```bash
git add packages/lexigram-auth/src/lexigram/auth/mfa/manager.py packages/lexigram-auth/tests/unit/test_mfa_manager_config.py
git commit -m "✨ feat(auth): MFAManager reads TOTP/backup settings from MFAConfig"
```

---

## Task 4: Update `MFAProvider` and `AuthBundleProvider` wiring

**Files:**
- Modify: `packages/lexigram-auth/src/lexigram/auth/di/sub_providers/mfa_provider.py`
- Modify: `packages/lexigram-auth/src/lexigram/auth/di/bundle_provider.py`

**Interfaces:**
- Consumes: `AuthConfig` (which now contains `MFAConfig`)
- Produces: `MFAProvider` registers `MFAManager` with config; `AuthBundleProvider` includes `MFAProvider` in sub-providers

**Pattern reference:** `TokenProvider` (`token_provider.py`) — accepts `config: AuthConfig | None` in constructor, no `config_key`/`config_model`, registered by `AuthBundleProvider._compose_sub_providers()`.

- [ ] **Step 1: Rewrite `MFAProvider` to follow sub-provider pattern**

Replace the placeholder `mfa_provider.py` with:

```python
"""MFA provider — registers MFAManager with config from AuthConfig.

Follows the sub-provider pattern (like TokenProvider, SessionProvider):
receives AuthConfig via constructor, no config_key/config_model.
"""
from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any

from lexigram.auth.config import AuthConfig, MFAConfig
from lexigram.auth.mfa.manager import MFAManager
from lexigram.contracts.core import HealthCheckResult, HealthStatus, ProviderPriority
from lexigram.di.decorators import inject
from lexigram.di.markers import Inject
from lexigram.di.provider import Provider
from lexigram.logging import get_logger

if TYPE_CHECKING:
    from lexigram.contracts.core.di import (
        ContainerRegistrarProtocol,
        ContainerResolverProtocol,
    )

logger = get_logger(__name__)


@inject
class MFAProvider(Provider):
    """Register the MFA manager with config-driven TOTP/backup settings.

    Sub-provider managed by AuthBundleProvider. Receives AuthConfig via
    constructor (same pattern as TokenProvider, SessionProvider).

    Args:
        config: The resolved auth config (carries ``mfa`` section).
    """

    def __init__(
        self,
        config: Annotated[AuthConfig, Inject] | None = None,
    ) -> None:
        super().__init__(name="mfa", priority=ProviderPriority.SECURITY)
        self._config = config

    async def register(self, container: ContainerRegistrarProtocol) -> None:
        """Register MFAManager with MFAConfig from AuthConfig.

        The factory resolves UserStoreProtocol at resolution time (after
        AuthenticationProvider has registered it).
        """
        mfa_config = self._config.mfa if self._config else MFAConfig()

        async def build_mfa(resolver: Any) -> MFAManager:
            from lexigram.auth.storage.token_store import UserStoreProtocol

            user_store = await resolver.resolve(UserStoreProtocol)
            return MFAManager(user_store=user_store, config=mfa_config)

        container.singleton(MFAManager, factory=build_mfa)

    async def boot(self, container: ContainerResolverProtocol) -> None:
        """Initialize MFA provider."""
        logger.info("mfa_provider.booted")

    async def shutdown(self) -> None:
        """Shutdown MFA provider."""
        logger.info("mfa_provider.shutdown")

    async def health_check(self, timeout: float = 5.0) -> HealthCheckResult:
        """Check MFA provider health."""
        mfa_config = self._config.mfa if self._config else MFAConfig()
        return HealthCheckResult(
            component=self.name,
            status=HealthStatus.HEALTHY,
            details={
                "totp_digits": mfa_config.totp.digits,
                "totp_interval": mfa_config.totp.interval,
                "backup_count": mfa_config.backup.count,
                "max_attempts": mfa_config.max_challenge_attempts,
            },
        )


__all__ = [
    "MFAProvider",
    "logger",
]
```

- [ ] **Step 2: Update `AuthBundleProvider` to include `MFAProvider`**

In `bundle_provider.py`:

1. Add import:
```python
from lexigram.auth.di.sub_providers.mfa_provider import MFAProvider
```

2. In `_compose_sub_providers()`, after `self._admin = AuthAdminProvider(config=cfg)`, add:
```python
        self._mfa = MFAProvider(config=cfg)
```

3. Add `self._mfa` to `self._sub_providers` list (after `self._admin`):
```python
        self._sub_providers = [
            self._authn,
            self._token,
            self._session,
            self._authz,
            self._admin,
            self._mfa,
        ]
```

- [ ] **Step 3: Run full auth test suite**

Run: `uv run pytest packages/lexigram-auth/tests/ -v --tb=short 2>&1 | tail -20`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add packages/lexigram-auth/src/lexigram/auth/di/sub_providers/mfa_provider.py packages/lexigram-auth/src/lexigram/auth/di/bundle_provider.py
git commit -m "✨ feat(auth): MFAProvider registers MFAManager with config; bundle wires it"
```

---

## Task 5: Update auth-mfa demo to use `auth.mfa` config

**Files:**
- Modify: `demos/auth-mfa/application.yaml`
- Modify: `demos/auth-mfa/src/mfa_console/controllers/api.py`
- Modify: `demos/auth-mfa/src/mfa_console/di/provider.py`

**Interfaces:**
- Consumes: `MFAConfig` from `AuthConfig.mfa`
- Produces: Demo reads `max_challenge_attempts` from config; redundant `build_mfa` factory removed

- [ ] **Step 1: Add `auth.mfa` section to `application.yaml`**

After the `auth.roles` section, add:

```yaml
  # ── MFA ──────────────────────────────────────────────────────────────────
  # Multi-factor authentication: TOTP enrollment, backup codes, challenge
  # attempt limits.  The MFAManager reads these values at boot.
  mfa:
    enabled: true
    totp:
      digits: 6               # number of TOTP digits
      interval: 30            # time-step period in seconds
      valid_window: 1         # +/- time steps to accept
    backup:
      issuer: auth-mfa-demo   # label shown in authenticator apps
      count: 10               # number of backup codes
      length: 8               # length of each code
    max_challenge_attempts: 3 # failed attempts before session revoke
```

- [ ] **Step 2: Update `controllers/api.py` to accept and use config**

In `MfaApiController.__init__`, add `config: AuthConfig` parameter and read `max_challenge_attempts`:

```python
from lexigram.auth.config import AuthConfig

class MfaApiController(Controller):
    def __init__(
        self,
        authentication: AuthenticationService,
        users: UserService,
        mfa: MFAManager,
        cookies: SessionCookieBackend,
        sessions: InMemorySessionRepository,
        config: AuthConfig,
    ) -> None:
        ...
        self._max_attempts = config.mfa.max_challenge_attempts
```

Replace `MAX_CHALLENGE_ATTEMPTS` usage in `challenge()` with `self._max_attempts`.

Remove the module-level `MAX_CHALLENGE_ATTEMPTS = 3` constant.

- [ ] **Step 3: Update `di/provider.py` — remove redundant `build_mfa`, pass config to controller**

The framework's `MFAProvider` (in `AuthBundleProvider`) now registers `MFAManager` as a singleton. The demo's `build_mfa` factory is redundant and should be removed.

1. Remove the `build_mfa` factory and its `container.singleton(MFAManager, ...)` registration.

2. Update `build_api` to pass `AuthConfig`:
```python
        async def build_api(resolver):
            return MfaApiController(
                authentication=await resolver.resolve(AuthenticationService),
                users=await resolver.resolve(UserService),
                mfa=await resolver.resolve(MFAManager),
                cookies=await resolver.resolve(SessionCookieBackend),
                sessions=await resolver.resolve(InMemorySessionRepository),
                config=await resolver.resolve(AuthConfig),
            )
```

- [ ] **Step 4: Run demo tests**

Run: `uv run pytest demos/auth-mfa/tests/ -v`
Expected: All tests pass

- [ ] **Step 5: Commit**

```bash
git add demos/auth-mfa/application.yaml demos/auth-mfa/src/mfa_console/controllers/api.py demos/auth-mfa/src/mfa_console/di/provider.py
git commit -m "✨ feat(demo): auth-mfa reads MFA settings from application.yaml"
```

---

## Task 6: Verify end-to-end and clean up

**Files:**
- (no new files)

- [ ] **Step 1: Run full auth test suite**

Run: `uv run pytest packages/lexigram-auth/tests/ -v --tb=short`
Expected: All tests pass

- [ ] **Step 2: Run auth-mfa demo tests**

Run: `uv run pytest demos/auth-mfa/tests/ -v`
Expected: All tests pass

- [ ] **Step 3: Run lint and format check**

Run: `uv run ruff check packages/lexigram-auth/src/lexigram/auth/config.py packages/lexigram-auth/src/lexigram/auth/mfa/manager.py packages/lexigram-auth/src/lexigram/auth/di/sub_providers/mfa_provider.py packages/lexigram-auth/src/lexigram/auth/di/bundle_provider.py demos/auth-mfa/src/mfa_console/controllers/api.py demos/auth-mfa/src/mfa_console/di/provider.py`

Run: `uv run ruff format --check packages/lexigram-auth/src/lexigram/auth/config.py packages/lexigram-auth/src/lexigram/auth/mfa/manager.py demos/auth-mfa/src/mfa_console/controllers/api.py`

Expected: No errors

- [ ] **Step 4: Commit any lint fixes**

```bash
git add -A
git commit -m "🎨 style(auth): lint and format fixes for MFA config"
```

---

## Verification Checklist

After all tasks complete, verify:

1. `application.yaml` → `auth.mfa.totp.digits`, `auth.mfa.backup.issuer`, `auth.mfa.max_challenge_attempts` are all configurable
2. `MFAManager.enable_totp()` uses `config.backup.issuer` by default (no hardcoded `"lexigram"`)
3. `MFAManager.verify_totp()` uses `config.totp.valid_window` (no hardcoded `window=1`)
4. `MFAManager.enable_totp()` passes `config.backup.count` and `config.backup.length` to `generate_backup_codes()`
5. `MFAProvider` follows sub-provider pattern (constructor injection, no `config_key`/`config_model`)
6. `AuthBundleProvider` includes `MFAProvider` in sub-providers list
7. `MfaApiController` reads `max_challenge_attempts` from `AuthConfig.mfa`
8. Demo no longer has redundant `build_mfa` factory
9. Demo yaml has `auth.mfa:` section with all available keys (uncommented)
10. All existing tests pass
11. New unit tests cover config defaults, custom values, and MFAManager config usage

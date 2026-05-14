from __future__ import annotations

import pytest

from lexigram.secrets.config import SecretsConfig


class TestSecretsConfig:
    def test_defaults(self) -> None:
        cfg = SecretsConfig()
        assert cfg.enabled
        assert cfg.backend_type == "memory"
        assert cfg.max_age_seconds == 7776000.0
        assert cfg.tenant_id is None

    def test_tenant_id_set(self) -> None:
        cfg = SecretsConfig(tenant_id="acme")
        assert cfg.tenant_id == "acme"

    def test_custom_actor_id(self) -> None:
        cfg = SecretsConfig(audit_actor_id="my-bot")
        assert cfg.audit_actor_id == "my-bot"

    def test_unknown_backend_type(self) -> None:
        cfg = SecretsConfig(backend_type="nonexistent")
        assert cfg.backend_type == "nonexistent"

    def test_backend_options(self) -> None:
        cfg = SecretsConfig(
            backend_type="vault",
            backend_options={"url": "http://vault:8200"},
        )
        assert cfg.backend_options["url"] == "http://vault:8200"


class TestSecretsEnvironmentDerivation:
    def test_is_production_derives_from_environment(self, monkeypatch) -> None:
        monkeypatch.setenv("LEX_ENV", "production")
        prod = SecretsConfig(backend_type="vault")
        assert prod.is_production is True
        assert prod.is_development is False
        assert prod.is_test is False

    def test_is_development_derives_from_environment(self, monkeypatch) -> None:
        monkeypatch.setenv("LEX_ENV", "development")
        dev = SecretsConfig(backend_type="vault")
        assert dev.is_production is False
        assert dev.is_development is True
        assert dev.is_test is False

    def test_is_test_derives_from_environment(self, monkeypatch) -> None:
        monkeypatch.setenv("LEX_ENV", "test")
        test = SecretsConfig(backend_type="vault")
        assert test.is_production is False
        assert test.is_development is False
        assert test.is_test is True

    def test_production_memory_backend_raises(self, monkeypatch) -> None:
        monkeypatch.setenv("LEX_ENV", "production")
        with pytest.raises(ValueError, match="LEX_SECRETS__BACKEND_TYPE"):
            SecretsConfig(backend_type="memory")

    def test_staging_memory_backend_raises(self, monkeypatch) -> None:
        monkeypatch.setenv("LEX_ENV", "staging")
        with pytest.raises(ValueError, match="memory"):
            SecretsConfig(backend_type="memory")

    def test_production_cloud_backend_ok_when_configured(self, monkeypatch) -> None:
        monkeypatch.setenv("LEX_ENV", "production")
        cfg = SecretsConfig(
            backend_type="vault",
            backend_options={"url": "https://vault:8200", "token": "x" * 40},
        )
        assert cfg.is_production is True

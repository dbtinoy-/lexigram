from __future__ import annotations

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

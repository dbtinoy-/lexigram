from __future__ import annotations


def test_admin_data_config_defaults_to_five_second_timeout() -> None:
    from lexigram.admin.config import AdminConfig

    cfg = AdminConfig()
    assert cfg.data.query_timeout_seconds == 5

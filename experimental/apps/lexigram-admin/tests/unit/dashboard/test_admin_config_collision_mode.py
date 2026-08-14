def test_collision_mode_defaults_to_warn() -> None:
    from lexigram.admin.config import AdminConfig

    cfg = AdminConfig()
    assert cfg.contributor_collision_mode == "warn"


def test_collision_mode_accepts_error() -> None:
    from lexigram.admin.config import AdminConfig

    cfg = AdminConfig(contributor_collision_mode="error")
    assert cfg.contributor_collision_mode == "error"

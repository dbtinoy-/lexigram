from shorts_creator.ui.components.provider_card import ProviderCard


def _card(model):
    return ProviderCard({"name": "opencode", "model": model, "enabled": True, "status": "healthy"})


def test_model_is_prominent_and_name_preserved():
    html = _card("deepseek-v4-flash-free")
    assert "deepseek-v4-flash-free" in html
    assert "opencode" in html
    assert "Ready" in html


def test_model_is_styled_bold_before_muted_name():
    html = _card("deepseek-v4-flash-free")
    assert "font-semibold text-sm font-mono" in html
    assert "text-foreground font-semibold text-sm font-mono" in html
    assert "text-muted-foreground text-[10px] font-mono ml-2 capitalize" in html
    model_pos = html.index("deepseek-v4-flash-free")
    name_pos = html.index("opencode")
    assert model_pos < name_pos


def test_duplicate_names_disambiguated_by_model():
    a = _card("deepseek-v4-flash-free")
    b = _card("laguna-s-2.1-free")
    assert "laguna-s-2.1-free" not in a
    assert "deepseek-v4-flash-free" not in b

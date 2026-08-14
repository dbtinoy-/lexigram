from lexigram.ui import Badge, Spinner, render_to_string


def test_badge_renders_text_and_variant_classes():
    html = render_to_string(Badge("New", variant="success"))
    assert "New" in html
    assert "bg-success" in html
    assert "rounded-full" in html


def test_badge_unknown_variant_falls_back_to_default():
    html = render_to_string(Badge("X", variant="mystery"))
    assert "X" in html
    assert "bg-muted" in html


def test_spinner_svg_and_size():
    html = render_to_string(Spinner(size="sm"))
    assert html.startswith("<svg")
    assert "w-4 h-4" in html
    assert "text-primary" in html
    assert 'viewBox="0 0 24 24"' in html


def test_spinner_contains_circle_and_path():
    html = render_to_string(Spinner())
    assert "<circle" in html
    assert "<path" in html

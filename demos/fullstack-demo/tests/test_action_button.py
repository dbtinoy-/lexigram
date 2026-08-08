from shorts_creator.ui.button import ActionButton


class TestActionButtonRenders:
    def test_renders_label_and_reserved_spinner_slot(self):
        html = str(ActionButton("Generate SEO"))
        assert "Generate SEO" in html
        assert "htmx-indicator" in html
        assert "w-4 h-4 shrink-0" in html

    def test_hx_disabled_elt_on_mutating_requests(self):
        html = str(ActionButton("Save", hx_post="/api/save"))
        assert 'hx-disabled-elt="this"' in html
        assert 'hx-post="/api/save"' in html

    def test_no_hx_disabled_elt_on_get(self):
        html = str(ActionButton("Open", hx_get="/api/open"))
        assert "hx_disabled_elt" not in html
        assert 'hx-get="/api/open"' in html

    def test_disabled_attribute_and_styles(self):
        html = str(ActionButton("Create", hx_post="/api/create", disabled=True))
        assert "disabled" in html
        assert "disabled:opacity-50" in html
        assert "cursor-not-allowed" in html

    def test_variants_map_to_expected_classes(self):
        primary = str(ActionButton("A", hx_post="/x"))
        success = str(ActionButton("B", variant="success", hx_post="/x"))
        ghost = str(ActionButton("C", variant="ghost", hx_post="/x"))
        danger = str(ActionButton("D", variant="danger", hx_post="/x"))
        assert "bg-primary hover:bg-primary/90" in primary
        assert "bg-success hover:bg-success/90" in success
        assert "from-primary" not in primary
        assert "from-success" not in success
        assert "bg-secondary hover:bg-secondary/80" in ghost
        assert "text-destructive" in danger

    def test_hx_confirm_and_target_passthrough(self):
        html = str(
            ActionButton(
                "Delete",
                variant="danger",
                hx_post="/api/delete",
                hx_target="#list",
                hx_swap="innerHTML",
                hx_confirm="Delete this?",
            )
        )
        assert 'hx-confirm="Delete this?"' in html
        assert 'hx-target="#list"' in html
        assert 'hx-swap="innerHTML"' in html

    def test_icon_rendered_before_label(self):
        from shorts_creator.ui.icons import zap

        html = str(ActionButton("Go", icon=zap(), hx_post="/x"))
        assert html.index("svg") < html.index("Go")

    def test_id_and_title_passthrough(self):
        html = str(ActionButton("X", hx_post="/x", id="btn-1", title="Tip"))
        assert 'id="btn-1"' in html
        assert 'title="Tip"' in html

    def test_sizes(self):
        sm = str(ActionButton("S", size="sm", hx_post="/x"))
        md = str(ActionButton("M", size="md", hx_post="/x"))
        assert "px-3 py-1.5" in sm
        assert "px-4 py-2" in md


def test_outline_variant_has_no_success_hover():
    html = str(ActionButton("X", variant="outline", hx_post="/x"))
    assert "hover:text-success" not in html
    assert "hover:text-foreground" in html

from shorts_creator.ui.components.run_history import Badge


class TestBadge:
    def test_rendering_and_draft_get_distinct_non_default_colors(self):
        rendering = Badge("rendering")
        draft = Badge("draft")
        assert "primary" in rendering
        assert "card/50" in draft
        assert rendering != draft

    def test_underscored_status_renders_as_readable_label(self):
        assert "Idea Selected" in Badge("idea_selected")
        assert "Idea_Selected" not in Badge("idea_selected")

    def test_existing_history_statuses_unchanged(self):
        assert "success" in Badge("completed")
        assert "destructive" in Badge("failed")

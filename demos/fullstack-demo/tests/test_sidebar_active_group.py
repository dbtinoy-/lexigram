from shorts_creator.ui.shell import AppLayout


class TestSidebarActiveGroup:
    def test_sidebar_has_correct_sections(self):
        html = AppLayout()._sidebar()
        assert "/api/sidebar/recent-projects" in html
        assert 'id="sidebar-recent-projects"' in html
        assert '/api/sidebar/recent-runs"' in html
        assert 'id="sidebar-recent-runs"' in html
        assert 'hx-vals="js:{project_id:' in html
        assert "sidebarRunsChanged from:body" in html
        assert "PROJECT" in html
        assert "RUNS" in html
        assert "LIBRARY" in html
        assert "CONFIGURE" in html
        assert "WORKSPACE" not in html
        assert "/history" in html
        assert "/api/sidebar/active" not in html
        assert "sidebar-project-dropdown" not in html
        assert "sidebar-runs-see-all" not in html

    def test_videos_link_lives_only_in_project_section(self):
        """The /videos page is project-scoped, so the sidebar must not
        duplicate it: LIBRARY keeps History and Assets, and project links
        live in the PROJECT section (recent projects list)."""
        html = AppLayout()._sidebar()
        assert "/videos" not in html
        assert "LIBRARY" in html
        library = html.split("LIBRARY")[1].split("CONFIGURE")[0]
        assert "History" in library
        assert "Videos" not in library

    def test_configure_holds_config_and_library_holds_assets(self):
        html = AppLayout()._sidebar()
        library = html.split("LIBRARY")[1].split("CONFIGURE")[0]
        configure = html.split("CONFIGURE")[1]
        assert "Assets" in library
        assert "History" in library
        assert "Topics" in configure
        assert "Settings" in configure
        assert "Assets" not in configure

    def test_sidebar_has_collapse_toggle(self):
        html = AppLayout()._sidebar()
        assert 'id="sidebar-toggle"' in html
        assert 'onclick="toggleSidebar()"' in html
        assert "sidebar-collapsed" not in html

    def test_sidebar_active_supports_sub_page_fallbacks(self):
        """Section links must be able to highlight on sub pages: "See All"
        (/projects) and "All runs" (/projects/{id}/runs) carry no
        data-no-active suppression, and icon-only links retain their
        label for full-width mode."""
        html = AppLayout()._sidebar()
        assert "data-no-active" not in html
        assert "data_no_active" not in html
        assert "side-icon-link" in html
        assert "side-label" in html
        assert "chevron-wrap" in html

    def test_links_use_distinct_matching_icons(self):
        html = AppLayout()._sidebar()
        library = html.split("LIBRARY")[1].split("CONFIGURE")[0]
        configure = html.split("CONFIGURE")[1]
        history_svg = library.split("History")[0].rsplit("<svg", 1)[1].split("</svg>")[0]
        assets_svg = library.split("Assets")[0].rsplit("<svg", 1)[1].split("</svg>")[0]
        topics_svg = configure.split("Topics")[0].rsplit("<svg", 1)[1].split("</svg>")[0]
        settings_svg = configure.split("Settings")[0].rsplit("<svg", 1)[1].split("</svg>")[0]
        assert history_svg != assets_svg
        assert topics_svg != settings_svg

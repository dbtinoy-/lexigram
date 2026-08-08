from shorts_creator.controllers.homepage import HomepageController


class TestHomepageRootRedirect:
    async def test_root_redirects_to_projects(self):
        controller = HomepageController()
        response = await controller.root(request=None)
        assert response.status_code == 302
        assert response.headers["location"] == "/projects"

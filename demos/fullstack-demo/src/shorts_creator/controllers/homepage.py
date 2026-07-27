from lexigram.web import Controller, HTMLContent, get
from starlette.responses import RedirectResponse


class HomepageController(Controller):
    @get("/")
    async def root(self, request=None) -> HTMLContent:
        return RedirectResponse(url="/projects", status_code=302)

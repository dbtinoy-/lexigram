from lexigram.web import Controller, FileResponse, HTMLContent, get, html_response, post

from shorts_creator.controllers.api.ideas_api import toast
from shorts_creator.models.asset import CLIP_ROLES
from shorts_creator.services.asset_service import AssetService


class AssetsApiController(Controller):
    def __init__(self, service: AssetService):
        self.service = service

    @post("/api/assets/upload")
    async def upload(self, request=None) -> HTMLContent:
        form = await request.form() if request else {}
        asset_type = str(form.get("type", ""))
        name = str(form.get("name", "")).strip()
        role = str(form.get("role", "")).strip() or None
        description = str(form.get("description", "")).strip()
        tags = [t.strip() for t in str(form.get("tags", "")).split(",") if t.strip()]
        upload = form.get("file")
        if upload is None or not getattr(upload, "filename", ""):
            return HTMLContent(toast("No file provided"))
        data = await upload.read()
        filename = upload.filename or ""
        ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
        try:
            await self.service.create_asset(
                asset_type,
                name or filename,
                data,
                ext,
                description=description,
                tags=tags,
                role=role,
            )
        except ValueError as exc:
            return HTMLContent(toast(f"Upload failed: {exc}"))
        return HTMLContent(toast("Asset saved"))

    @post("/api/assets/{id}/update")
    async def update(self, request=None, id: str = "") -> HTMLContent:
        form = await request.form() if request else {}
        updates: dict = {}
        if "name" in form:
            updates["name"] = str(form["name"]).strip()
        if "description" in form:
            updates["description"] = str(form["description"]).strip()
        if "tags" in form:
            updates["tags"] = [t.strip() for t in str(form["tags"]).split(",") if t.strip()]
        if "role" in form:
            role = str(form["role"]).strip()
            if role != "" and role in CLIP_ROLES:
                updates["role"] = role
        if updates and not await self.service.update_asset(id, updates):
            return HTMLContent(toast("Asset not found"))
        return HTMLContent(toast("Asset updated"))

    @post("/api/assets/{id}/delete")
    async def delete(self, request=None, id: str = "") -> HTMLContent:
        if not await self.service.delete_asset(id):
            return HTMLContent(toast("Asset not found"))
        return HTMLContent(toast("Asset deleted"))

    @get("/api/assets/select-options")
    async def select_options(self, request=None) -> HTMLContent:
        qp = getattr(request, "query_params", {}) if request else {}
        asset_type = qp.get("type", "")
        role = qp.get("role", "")
        assets = await self.service.list_by_type(asset_type, role or None)
        options = ["<option value=''>None (built-in)</option>"]
        options += [
            f"<option value='{a.id}'>{a.name.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')}</option>"
            for a in assets
        ]
        return HTMLContent("".join(options))

    @get("/api/assets/{id}/file")
    async def file(self, request=None, id: str = "") -> FileResponse:
        asset = await self.service.get(id)
        if not asset or not asset.file_path:
            return html_response("Not found", status_code=404)
        path = self.service.absolute_path(asset.file_path)
        if not path.exists():
            return html_response("File missing", status_code=404)
        return FileResponse(
            str(path), media_type=asset.meta.get("mime", "application/octet-stream")
        )

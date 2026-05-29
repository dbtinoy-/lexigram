"""End-to-end tests for import download endpoints through the mounted admin app."""

from __future__ import annotations

from typing import Any

import httpx
import pytest
from starlette.applications import Starlette

from lexigram.admin.actions.standard import ImportAction
from lexigram.admin.config import AdminConfig
from lexigram.admin.core.routing import AdminRouter
from lexigram.admin.resources.base import Resource
from lexigram.admin.services.import_ import AdminImportService


class _RejectingDataSource:
    """Data source whose create() fails for row 1."""

    def __init__(self) -> None:
        self.created: list[dict[str, Any]] = []

    async def create(self, row: dict[str, Any]) -> Any:
        if row.get("_row") == 1:
            raise ValueError("boom at row 1")
        self.created.append(row)
        return row


def _mount(resource: type[Resource]) -> Starlette:
    app = Starlette()
    router = AdminRouter(
        config=AdminConfig(prefix="/admin"),
        resources={"users": resource},
    )
    router.mount(app)
    return app


@pytest.mark.asyncio
async def test_import_example_endpoint_returns_csv_attachment() -> None:
    class UsersResource(Resource):
        header_actions = [
            ImportAction(
                example_columns=["name", "email"],
                example_filename="users-template.csv",
            )
        ]

    app = _mount(UsersResource)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/admin/users/import-example")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/csv")
    assert (
        'attachment; filename="users-template.csv"'
        in response.headers["content-disposition"]
    )
    assert response.text == "name,email\n"


@pytest.mark.asyncio
async def test_import_example_endpoint_404_when_not_configured() -> None:
    class UsersResource(Resource):
        pass

    app = _mount(UsersResource)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/admin/users/import-example")

    assert response.status_code == 404


@pytest.mark.asyncio
async def test_import_report_endpoint_returns_csv_attachment() -> None:
    service = AdminImportService(_RejectingDataSource(), required_fields=["name"])
    job = (await service.parse(b"name\nA\nB", "users.csv")).unwrap()
    job.rows = [{"_row": 1, "name": "A"}, {"_row": 2, "name": "B"}]
    job.total_rows = 2
    await service.commit(job)
    report_id = service.reports()[0].id

    class UsersResource(Resource):
        header_actions = [ImportAction(import_service=service)]

    app = _mount(UsersResource)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get(f"/admin/users/import-report?report_id={report_id}")

    assert response.status_code == 200
    assert "users-import-errors.csv" in response.headers["content-disposition"]
    assert response.text.startswith("row,field,message")
    assert "1,__row__," in response.text


@pytest.mark.asyncio
async def test_import_report_endpoint_404_for_unknown_report() -> None:
    class UsersResource(Resource):
        header_actions = [
            ImportAction(import_service=AdminImportService(_RejectingDataSource()))
        ]

    app = _mount(UsersResource)
    async with httpx.AsyncClient(
        transport=httpx.ASGITransport(app=app), base_url="http://testserver"
    ) as client:
        response = await client.get("/admin/users/import-report?report_id=nope")

    assert response.status_code == 404

from __future__ import annotations

import tempfile
from pathlib import Path

from lexigram.codegen import ServiceGenerator


def test_service_generates_crud_methods():
    with tempfile.TemporaryDirectory() as tmp:
        gen = ServiceGenerator(output_dir=tmp)
        result = gen.generate("Message")
        assert len(result.files_created) == 1
        file_path = result.files_created[0]
        content = Path(file_path).read_text()
        assert "class MessageService" in content
        assert "async def list(self)" in content
        assert "async def get(self, item_id: int)" in content
        assert "async def create(self" in content
        assert "async def update(self, item_id: int" in content
        assert "async def delete(self, item_id: int" in content


def test_service_no_double_suffix():
    with tempfile.TemporaryDirectory() as tmp:
        gen = ServiceGenerator(output_dir=tmp)
        result = gen.generate("MessageService")
        file_path = result.files_created[0]
        assert not str(file_path).endswith("_service_service.py")
        assert str(file_path).endswith("_service.py")

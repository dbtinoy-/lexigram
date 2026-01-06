from __future__ import annotations

import tempfile
from pathlib import Path

from lexigram.web.cli.generators import ControllerGenerator


def test_controller_uses_resource_path():
    with tempfile.TemporaryDirectory() as tmp:
        gen = ControllerGenerator(output_dir=tmp)
        result = gen.generate("Message", path="/api/messages")
        file_path = result.files_created[0]
        content = Path(file_path).read_text()
        assert '@get("/api/messages")' in content
        assert '@get("/api/messages/{id}")' in content
        assert '@post("/api/messages")' in content
        assert '@put("/api/messages/{id}")' in content
        assert '@delete("/api/messages/{id}")' in content


def test_controller_calls_service_crud():
    with tempfile.TemporaryDirectory() as tmp:
        gen = ControllerGenerator(output_dir=tmp)
        result = gen.generate("Message")
        file_path = result.files_created[0]
        content = Path(file_path).read_text()
        assert "self.service.list(" in content
        assert "self.service.get(" in content
        assert "self.service.create(" in content
        assert "self.service.update(" in content
        assert "self.service.delete(" in content


def test_controller_no_double_suffix():
    with tempfile.TemporaryDirectory() as tmp:
        gen = ControllerGenerator(output_dir=tmp)
        result = gen.generate("MessageController")
        file_path = result.files_created[0]
        assert not str(file_path).endswith("_controller_controller.py")
        content = Path(file_path).read_text()
        assert "class MessageController(Controller)" in content

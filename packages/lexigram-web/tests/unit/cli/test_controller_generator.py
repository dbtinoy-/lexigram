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
        assert '@get("/api/messages/{item_id}")' in content
        assert '@post("/api/messages", status_code=201)' in content
        assert '@put("/api/messages/{item_id}")' in content
        assert '@delete("/api/messages/{item_id}")' in content


def test_controller_delegates_to_repo():
    with tempfile.TemporaryDirectory() as tmp:
        gen = ControllerGenerator(output_dir=tmp)
        gen.generate("Message")
        content = Path(tmp, "message_controller.py").read_text()
        assert "self.repo.list(" in content
        assert "self.repo.get(" in content
        assert "self.repo.create(" in content
        assert "self.repo.update(" in content
        assert "self.repo.delete(" in content


def test_controller_no_double_suffix():
    with tempfile.TemporaryDirectory() as tmp:
        gen = ControllerGenerator(output_dir=tmp)
        result = gen.generate("MessageController")
        file_path = result.files_created[0]
        assert not str(file_path).endswith("_controller_controller.py")
        content = Path(file_path).read_text()
        assert "class MessageController(Controller)" in content
        assert "Service" not in content

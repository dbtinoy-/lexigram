from __future__ import annotations

import tempfile
from pathlib import Path

from lexigram.codegen import ModelGenerator


def test_model_uses_correct_func_import():
    with tempfile.TemporaryDirectory() as tmp:
        gen = ModelGenerator(output_dir=tmp)
        result = gen.generate("Message", fields_str="content:text")
        file_path = result.files_created[0]
        content = Path(file_path).read_text()
        assert "from sqlalchemy import" in content
        assert "from sqlalchemy.sql import func" not in content
        assert "func.now()" in content


def test_user_specified_id_gets_primary_key():
    with tempfile.TemporaryDirectory() as tmp:
        gen = ModelGenerator(output_dir=tmp)
        result = gen.generate("Message", fields_str="id:int,content:text")
        file_path = result.files_created[0]
        content = Path(file_path).read_text()
        assert content.count("id: Mapped[int]") == 1
        assert "primary_key=True" in content
        assert "autoincrement=True" in content

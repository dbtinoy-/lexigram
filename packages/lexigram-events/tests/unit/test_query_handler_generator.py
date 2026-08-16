from __future__ import annotations

from pathlib import Path
import py_compile
import tempfile

from lexigram.events.cli.generators.query_handler import QueryHandlerGenerator


class TestQueryHandlerGenerator:
    def setup_method(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())

    def test_generates_query_file(self) -> None:
        gen = QueryHandlerGenerator(output_dir=str(self.tmp_dir))
        result = gen.generate("GetUser", fields_str="user_id:str")
        assert len(result.files_created) == 1
        file_path = self.tmp_dir / "get_user.py"
        assert file_path.exists()

    def test_generated_file_is_valid_python(self) -> None:
        gen = QueryHandlerGenerator(output_dir=str(self.tmp_dir))
        gen.generate("ListOrders")
        file_path = self.tmp_dir / "list_orders.py"
        py_compile.compile(file_path, doraise=True)

    def test_generated_content_has_query_class(self) -> None:
        gen = QueryHandlerGenerator(output_dir=str(self.tmp_dir))
        gen.generate("GetUser", fields_str="user_id:str")
        content = (self.tmp_dir / "get_user.py").read_text()
        assert "GetUser" in content

    def test_dry_run_creates_no_files(self) -> None:
        gen = QueryHandlerGenerator(output_dir=str(self.tmp_dir))
        gen.generate("Widget", dry_run=True)
        assert not (self.tmp_dir / "widget.py").exists()

    def test_files_skipped_on_existing_without_force(self) -> None:
        gen = QueryHandlerGenerator(output_dir=str(self.tmp_dir))
        gen.generate("Item")
        result = gen.generate("Item")
        assert len(result.files_created) == 0

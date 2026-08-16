from __future__ import annotations

from pathlib import Path
import py_compile
import tempfile

from lexigram.sql.cli.generators.model import ModelGenerator


class TestModelGenerator:
    def setup_method(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())

    def test_generates_model_file(self) -> None:
        gen = ModelGenerator(output_dir=str(self.tmp_dir))
        result = gen.generate("User", fields_str="name:str,email:str!unique")
        assert len(result.files_created) == 1
        file_path = self.tmp_dir / "user.py"
        assert file_path.exists()

    def test_generated_file_is_valid_python(self) -> None:
        gen = ModelGenerator(output_dir=str(self.tmp_dir))
        gen.generate("Product", fields_str="title:str,price:float")
        file_path = self.tmp_dir / "product.py"
        py_compile.compile(file_path, doraise=True)

    def test_generated_content_has_expected_structure(self) -> None:
        gen = ModelGenerator(output_dir=str(self.tmp_dir))
        gen.generate("UserProfile", fields_str="name:str,email:str!unique")
        content = (self.tmp_dir / "user_profile.py").read_text()
        assert "class UserProfileModel(Base):" in content
        assert "__tablename__" in content
        assert "Mapped[str]" in content
        assert "unique=True" in content

    def test_generate_with_relationships(self) -> None:
        gen = ModelGenerator(output_dir=str(self.tmp_dir))
        gen.generate("Order", fields_str="total:float,user_id:int!fk=user")
        content = (self.tmp_dir / "order.py").read_text()
        assert "ForeignKey" in content
        assert "relationship" in content or "user" in content

    def test_dry_run_creates_no_files(self) -> None:
        gen = ModelGenerator(output_dir=str(self.tmp_dir))
        gen.generate("Widget", fields_str="name:str", dry_run=True)
        assert not (self.tmp_dir / "widget.py").exists()

    def test_files_skipped_on_existing_without_force(self) -> None:
        gen = ModelGenerator(output_dir=str(self.tmp_dir))
        gen.generate("Item", fields_str="name:str")
        result = gen.generate("Item", fields_str="name:str")
        assert len(result.files_skipped) == 1

    def test_force_overwrites_existing(self) -> None:
        gen = ModelGenerator(output_dir=str(self.tmp_dir))
        gen.generate("Item", fields_str="name:str")
        result = gen.generate("Item", fields_str="name:str", force=True)
        assert len(result.files_overwritten) == 1 or len(result.files_created) == 1

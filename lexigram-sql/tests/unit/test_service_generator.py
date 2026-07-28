from __future__ import annotations

from pathlib import Path
import py_compile
import tempfile

from lexigram.sql.cli.generators.model import ModelGenerator
from lexigram.sql.cli.generators.service import ServiceGenerator


class TestServiceGenerator:
    def setup_method(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())

    def test_generates_service_file(self) -> None:
        gen = ServiceGenerator(output_dir=str(self.tmp_dir))
        result = gen.generate("User")
        assert len(result.files_created) == 1
        file_path = self.tmp_dir / "user_service.py"
        assert file_path.exists()

    def test_generated_file_is_valid_python(self) -> None:
        gen = ServiceGenerator(output_dir=str(self.tmp_dir))
        gen.generate("Product")
        file_path = self.tmp_dir / "product_service.py"
        py_compile.compile(file_path, doraise=True)

    def test_generated_content_has_service_class(self) -> None:
        gen = ServiceGenerator(output_dir=str(self.tmp_dir))
        gen.generate("UserProfile")
        content = (self.tmp_dir / "user_profile_service.py").read_text()
        assert "class UserProfileService:" in content

    def test_dry_run_creates_no_files(self) -> None:
        gen = ServiceGenerator(output_dir=str(self.tmp_dir))
        gen.generate("Widget", dry_run=True)
        assert not (self.tmp_dir / "widget_service.py").exists()

    def test_files_skipped_on_existing_without_force(self) -> None:
        gen = ServiceGenerator(output_dir=str(self.tmp_dir))
        gen.generate("Item")
        result = gen.generate("Item")
        assert len(result.files_skipped) == 1

    def test_model_and_service_generated_names_agree(self) -> None:
        ModelGenerator(output_dir=str(self.tmp_dir)).generate("User")
        ServiceGenerator(output_dir=str(self.tmp_dir)).generate("User")

        model_content = (self.tmp_dir / "user.py").read_text()
        service_content = (self.tmp_dir / "user_service.py").read_text()

        assert "class UserModel(Base):" in model_content
        assert "from ..models.user import UserModel" in service_content
        assert "list[UserModel]" in service_content
        assert "UserModel | None" in service_content

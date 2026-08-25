from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

from lexigram.nosql.cli.generators.document_repository import DocumentRepositoryGenerator


class TestDocumentRepositoryGenerator:
    def setup_method(self) -> None:
        self.generator = DocumentRepositoryGenerator()

    def test_name(self) -> None:
        assert self.generator.name == "document-repository"

    def test_description(self) -> None:
        assert self.generator.description == "Generate a NoSQL document repository"

    def test_default_output_dir(self) -> None:
        assert self.generator.default_output_dir == "src/repositories"

    def test_to_pascal_case_snake_case(self) -> None:
        assert self.generator._to_pascal_case("user") == "User"
        assert self.generator._to_pascal_case("order_item") == "OrderItem"

    def test_to_pascal_case_kebab_case(self) -> None:
        assert self.generator._to_pascal_case("user-profile") == "UserProfile"

    def test_to_snake_case_pascal_case(self) -> None:
        assert self.generator._to_snake_case("User") == "user"
        assert self.generator._to_snake_case("OrderItem") == "order_item"

    def test_to_snake_case_kebab_case(self) -> None:
        assert self.generator._to_snake_case("user-profile") == "user_profile"

    def test_generate_creates_file(self, tmp_path: Path) -> None:
        output_dir = str(tmp_path)
        with patch.object(
            self.generator,
            "render_template",
            return_value="generated content",
        ):

            result = self.generator.generate("product", output_dir=output_dir)

            expected_file = tmp_path / "product_repository.py"
            assert expected_file.exists()
            assert expected_file.read_text() == "generated content"
            assert result.files_created is not None

    def test_generate_no_force_skips_existing(self, tmp_path: Path) -> None:
        output_dir = str(tmp_path)
        repo_file = tmp_path / "product_repository.py"
        repo_file.write_text("existing content")

        with patch.object(
            self.generator,
            "render_template",
            return_value="new content",
        ):

            result = self.generator.generate("product", output_dir=output_dir)

            assert repo_file.read_text() == "existing content"
            assert result.files_created is None or len(result.files_created) == 0

    def test_generate_with_fields_str(self, tmp_path: Path) -> None:
        output_dir = str(tmp_path)
        with patch.object(
            self.generator,
            "render_template",
            return_value="generated with fields",
        ):

            self.generator.generate(
                "item", output_dir=output_dir, fields_str="name:str,price:float"
            )
            result_file = tmp_path / "item_repository.py"
            assert result_file.exists()

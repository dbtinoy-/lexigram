from __future__ import annotations

from pathlib import Path
import py_compile
import tempfile

from lexigram.events.cli.generators.event_generator import EventGenerator


class TestEventGenerator:
    def setup_method(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())

    def test_generates_event_file(self) -> None:
        gen = EventGenerator(output_dir=str(self.tmp_dir))
        result = gen.generate("UserCreated", fields_str="user_id:str,email:str")
        assert result.files_created == [self.tmp_dir / "user_created_event.py"]
        file_path = self.tmp_dir / "user_created_event.py"
        assert file_path.exists()

    def test_generated_file_is_valid_python(self) -> None:
        gen = EventGenerator(output_dir=str(self.tmp_dir))
        gen.generate("OrderPlaced", fields_str="order_id:str,total:float")
        file_path = self.tmp_dir / "order_placed_event.py"
        py_compile.compile(file_path, doraise=True)

    def test_generated_content_has_event_class(self) -> None:
        gen = EventGenerator(output_dir=str(self.tmp_dir))
        gen.generate("UserCreated", fields_str="user_id:str")
        content = (self.tmp_dir / "user_created_event.py").read_text()
        assert "class UserCreatedEvent(DomainEvent):" in content

    def test_generated_event_uses_aware_utc_clock_from_base(self) -> None:
        """The scaffold must not hand-roll naive datetimes into user code."""
        gen = EventGenerator(output_dir=str(self.tmp_dir))
        gen.generate("UserCreated", fields_str="user_id:str")
        content = (self.tmp_dir / "user_created_event.py").read_text()
        assert "utcnow" not in content
        assert "datetime.now" not in content
        assert "occurred_at" in content  # documented on the base, not redefined

    def test_dry_run_creates_no_files_on_disk(self) -> None:
        gen = EventGenerator(output_dir=str(self.tmp_dir))
        result = gen.generate("Widget", fields_str="name:str", dry_run=True)
        assert result.files_created == [self.tmp_dir / "widget_event.py"]
        assert not (self.tmp_dir / "widget_event.py").exists()

    def test_files_skipped_on_existing_without_force(self) -> None:
        gen = EventGenerator(output_dir=str(self.tmp_dir))
        gen.generate("Item", fields_str="name:str")
        result = gen.generate("Item", fields_str="name:str")
        assert result.files_skipped == [self.tmp_dir / "item_event.py"]
        assert result.files_created == []

    def test_force_overwrites_existing_file(self) -> None:
        gen = EventGenerator(output_dir=str(self.tmp_dir))
        gen.generate("Item", fields_str="name:str")
        result = gen.generate("Item", fields_str="name:str", force=True)
        assert result.files_overwritten == [self.tmp_dir / "item_event.py"]

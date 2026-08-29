from __future__ import annotations

from pathlib import Path
import py_compile
import tempfile

from lexigram.events.cli.generators.event_handler import EventHandlerGenerator


class TestEventHandlerGenerator:
    def setup_method(self) -> None:
        self.tmp_dir = Path(tempfile.mkdtemp())

    def test_generates_handler_file(self) -> None:
        gen = EventHandlerGenerator(output_dir=str(self.tmp_dir))
        result = gen.generate("OrderPlaced")
        assert result.files_created == [self.tmp_dir / "order_placed_handler.py"]
        assert (self.tmp_dir / "order_placed_handler.py").exists()

    def test_generated_file_is_valid_python(self) -> None:
        gen = EventHandlerGenerator(output_dir=str(self.tmp_dir))
        gen.generate("OrderShipped")
        py_compile.compile(self.tmp_dir / "order_shipped_handler.py", doraise=True)

    def test_generated_content_follows_demo_on_event_convention(self) -> None:
        gen = EventHandlerGenerator(output_dir=str(self.tmp_dir))
        gen.generate("OrderPlaced")
        content = (self.tmp_dir / "order_placed_handler.py").read_text()
        assert "class OrderPlacedHandler:" in content
        assert "async def on_order_placed(self, event: Any) -> None:" in content
        assert "event_bus.subscribe" in content

    def test_dry_run_creates_no_files_on_disk(self) -> None:
        gen = EventHandlerGenerator(output_dir=str(self.tmp_dir))
        result = gen.generate("Widget", dry_run=True)
        assert result.files_created == [self.tmp_dir / "widget_handler.py"]
        assert not (self.tmp_dir / "widget_handler.py").exists()

    def test_files_skipped_on_existing_without_force(self) -> None:
        gen = EventHandlerGenerator(output_dir=str(self.tmp_dir))
        gen.generate("Item")
        result = gen.generate("Item")
        assert result.files_skipped == [self.tmp_dir / "item_handler.py"]
        assert result.files_created == []

    def test_force_overwrites_existing_file(self) -> None:
        gen = EventHandlerGenerator(output_dir=str(self.tmp_dir))
        gen.generate("Item")
        result = gen.generate("Item", force=True)
        assert result.files_overwritten == [self.tmp_dir / "item_handler.py"]

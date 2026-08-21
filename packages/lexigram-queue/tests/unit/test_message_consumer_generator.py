"""Tests for MessageConsumerGenerator."""

from pathlib import Path

from lexigram.queue.cli.generators.message_consumer import MessageConsumerGenerator


def test_message_consumer_generator_name():
    """Test generator metadata."""
    generator = MessageConsumerGenerator()
    assert generator.name == "message_consumer"
    assert "message queue consumer" in generator.description


def test_generate_writes_rendered_consumer(tmp_path: Path):
    """Generation renders the real template into the target directory."""
    output_dir = tmp_path / "consumers"

    generator = MessageConsumerGenerator(
        output_dir=str(output_dir), broker="kafka", queue="test_queue"
    )
    result = generator.generate(name="test")

    file_created = Path(result.files_created[0])
    assert file_created == output_dir / "test_consumer.py"
    content = file_created.read_text()
    assert "class TestConsumer(MessageConsumer):" in content
    assert 'topic = "test_queue"' in content
    assert "via the kafka broker" in content


def test_second_generation_skips_existing_file(tmp_path: Path):
    """Re-running without force skips instead of overwriting."""
    generator = MessageConsumerGenerator(output_dir=str(tmp_path / "consumers"))

    first = generator.generate(name="test")
    assert len(first.files_created) == 1

    second = generator.generate(name="test")
    assert len(second.files_created) == 0
    assert len(second.files_skipped) == 1


def test_force_overwrites_existing_file(tmp_path: Path):
    """force=True replaces an already-generated consumer."""
    generator = MessageConsumerGenerator(output_dir=str(tmp_path / "consumers"))
    generator.generate(name="test")

    result = generator.generate(name="test", force=True)
    assert len(result.files_overwritten) == 1


def test_fields_str_flows_into_template(tmp_path: Path):
    """Parsed fields appear in the rendered docstring."""
    generator = MessageConsumerGenerator(
        output_dir=str(tmp_path / "consumers"), fields_str="f1:int"
    )
    result = generator.generate(name="order")

    content = Path(result.files_created[0]).read_text()
    assert "- f1 (int)" in content


def test_relative_output_dir_refused_outside_project(
    tmp_path: Path, monkeypatch
):
    """Default relative dir at a project-less CWD raises before writing."""
    bare = tmp_path / "nowhere"
    bare.mkdir()
    monkeypatch.chdir(bare)

    try:
        MessageConsumerGenerator()
    except ValueError as exc:
        assert "--output-dir" in str(exc)
    else:
        raise AssertionError("expected ValueError for unresolvable relative dir")
    assert not (bare / "src").exists(), "refusal must not touch the filesystem"

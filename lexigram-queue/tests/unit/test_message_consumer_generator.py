"""Tests for MessageConsumerGenerator."""

import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch
from lexigram.queue.cli.generators.message_consumer import MessageConsumerGenerator


def test_message_consumer_generator_name():
    """Test generator metadata."""
    generator = MessageConsumerGenerator()
    assert generator.name == "message_consumer"
    assert "message queue consumer" in generator.description


@patch("lexigram.queue.cli.generators.message_consumer.PackageLoader")
@patch("lexigram.queue.cli.generators.message_consumer.Environment")
def test_message_consumer_generator_generate(mock_env_class, mock_loader, tmp_path):
    """Test generation process."""
    mock_env = mock_env_class.return_value
    mock_template = mock_env.get_template.return_value
    mock_template.render.return_value = "rendered content"

    output_dir = tmp_path / "consumers"

    generator = MessageConsumerGenerator(
        output_dir=str(output_dir),
        broker="kafka",
        queue="test_queue"
    )

    with patch.object(MessageConsumerGenerator, "_get_package_name", return_value="app.consumers"):
        result = generator.generate(name="test")

        assert len(result.files_created) == 1
        file_created = output_dir / "test_consumer.py"
        assert file_created.exists()
        assert file_created.read_text() == "rendered content"

        mock_env.get_template.assert_called_with("message_consumer.py.jinja2")
        mock_template.render.assert_called()

        result2 = generator.generate(name="test")
        assert len(result2.files_created) == 0


def test_message_consumer_generator_fields():
    """Test field parsing."""
    generator = MessageConsumerGenerator(fields_str="f1:int")

    with patch("lexigram.queue.cli.generators.message_consumer.parse_fields") as mock_parse:
        mock_parse.return_value = [{"name": "f1", "type": "int"}]

        with patch.object(MessageConsumerGenerator, "_get_package_name"), \
             patch("lexigram.queue.cli.generators.message_consumer.Environment"), \
             patch("lexigram.queue.cli.generators.message_consumer.open"):

            generator.generate(name="test")
            mock_parse.assert_called_with("f1:int")

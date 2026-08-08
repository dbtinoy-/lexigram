import tempfile
from pathlib import Path

import pytest

from shorts_creator.contracts import Severity
from shorts_creator.formats.loader import load_format

WITH_REQUIRES = """\
---
name: speech
label: Speech
description: Plain spoken-word captions
caption_styles: [highlight, plain]
default_caption_style: highlight
requires:
  script: [hook]
  voice: [tts_story]
  pipeline: [captions, background]
objectives: []
assets: []
---
"""

NO_REQUIRES = """\
---
name: plain
label: Plain
description: legacy format without contract fields
caption_styles: [highlight]
default_caption_style: highlight
---
"""

UNIMPLEMENTED_PIPELINE = """\
---
name: beats
label: Beats
description: beat-synced future format
caption_styles: [highlight]
default_caption_style: highlight
requires:
  script: [hook]
  voice: [tts_story]
  pipeline: [silent_frames]
---
"""

UNKNOWN_CAPABILITY = """\
---
name: typo
label: Typo
description: bad capability name
caption_styles: [highlight]
default_caption_style: highlight
requires:
  pipeline: [capetions]
---
"""


class TestFormatRequires:
    def test_requires_parsed(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "FORMAT.md"
            path.write_text(WITH_REQUIRES, encoding="utf-8")
            fmt = load_format(path)
            assert fmt.requires == {
                "script": ["hook"],
                "voice": ["tts_story"],
                "pipeline": ["captions", "background"],
            }
            assert fmt.objectives == []
            assert fmt.assets == []

    def test_requires_absent_defaults_empty(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "FORMAT.md"
            path.write_text(NO_REQUIRES, encoding="utf-8")
            fmt = load_format(path)
            assert fmt.requires == {}
            assert fmt.objectives == []
            assert fmt.assets == []

    def test_to_contract_side(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "FORMAT.md"
            path.write_text(WITH_REQUIRES, encoding="utf-8")
            side = load_format(path).to_contract_side()
        assert side.name == "speech"
        assert side.requires_script == frozenset({"hook"})
        assert side.requires_pipeline == frozenset({"captions", "background"})

    def test_unimplemented_pipeline_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "FORMAT.md"
            path.write_text(UNIMPLEMENTED_PIPELINE, encoding="utf-8")
            with pytest.raises(Exception) as excinfo:
                load_format(path)
        assert "silent_frames" in str(excinfo.value)

    def test_unknown_capability_raises(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / "FORMAT.md"
            path.write_text(UNKNOWN_CAPABILITY, encoding="utf-8")
            with pytest.raises(Exception) as excinfo:
                load_format(path)
        assert "capetions" in str(excinfo.value)


class TestRegistryStrictMode:
    def test_broken_format_file_skipped_in_boot_mode_and_reported(self):
        from shorts_creator.formats.registry import FormatRegistry

        with tempfile.TemporaryDirectory() as tmp:
            bad_dir = Path(tmp) / "broken"
            bad_dir.mkdir()
            (bad_dir / "FORMAT.md").write_text(UNIMPLEMENTED_PIPELINE, encoding="utf-8")
            good_dir = Path(tmp) / "ok"
            good_dir.mkdir()
            (good_dir / "FORMAT.md").write_text(WITH_REQUIRES, encoding="utf-8")
            r = FormatRegistry()
            count = r.load(tmp)  # boot mode: strict=False default
            assert count == 1
            assert r.has("speech")
            errs = r.errors()
            assert len(errs) == 1
            _, exc = errs[0]
            assert "silent_frames" in str(exc)

    def test_strict_load_raises_on_contract_violation(self):
        from shorts_creator.contracts.errors import ContractLoadError
        from shorts_creator.formats.registry import FormatRegistry

        with tempfile.TemporaryDirectory() as tmp:
            bad_dir = Path(tmp) / "broken"
            bad_dir.mkdir()
            (bad_dir / "FORMAT.md").write_text(UNIMPLEMENTED_PIPELINE, encoding="utf-8")
            r = FormatRegistry()
            with pytest.raises(ContractLoadError) as excinfo:
                r.load(tmp, strict=True)
        assert "silent_frames" in str(excinfo.value)

    def test_missing_frontmatter_is_non_contract_skip(self):
        from shorts_creator.formats.registry import FormatRegistry

        with tempfile.TemporaryDirectory() as tmp:
            bad_dir = Path(tmp) / "broken"
            bad_dir.mkdir()
            (bad_dir / "FORMAT.md").write_text("no frontmatter here", encoding="utf-8")
            r = FormatRegistry()
            assert r.load(tmp) == 0
            assert r.errors() == []
            assert not r.has("broken")


class TestRealFormatsContract:
    def test_narrated_contract_side(self):
        from shorts_creator.contracts import validate_pair
        from shorts_creator.formats import registry
        from shorts_creator.topics import registry as topics

        fmt = registry.get("narrated")
        assert fmt is not None
        side = fmt.to_contract_side()
        assert "hook" in side.requires_script
        assert "tts_story" in side.requires_voice
        assert side.requires_pipeline <= frozenset(
            {
                "word_timing",
                "captions",
                "background",
                "outro",
                "tts_story",
                "music_beat",
            }
        )
        for topic in topics.available:
            assert not any(
                i.severity is Severity.ERROR for i in validate_pair(topic.to_contract_side(), side)
            )

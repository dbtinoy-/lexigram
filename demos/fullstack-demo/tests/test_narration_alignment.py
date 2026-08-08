"""align_words: captions always show the script's own words.

Whisper's transcription of the Chatterbox voice is only a timing source -
tiny.en hears "The day" as "W" "-day" and "Every" as "W." "Every", and
those garbled strings used to be baked into the on-screen captions.
The realignment under test must recover the script text while keeping the
real timings, and must stay sane when Whisper mishears a whole line.
"""

import pytest

from shorts_creator.pipeline import narration
from shorts_creator.pipeline.pipeline import ReelPipeline
from shorts_creator.pipeline.render_config import RenderConfig


def _tokens(specs):
    return [{"word": w, "start": s, "end": e} for w, s, e in specs]


def test_clean_transcription_passes_through():
    line = "Your thumb keeps moving."
    words = _tokens(
        [
            ("Your", 0.0, 0.4),
            ("thumb", 0.4, 0.8),
            ("keeps", 0.8, 1.1),
            ("moving.", 1.1, 1.5),
        ]
    )
    out = narration.align_words(line, words)
    assert [w["word"] for w in out] == ["Your", "thumb", "keeps", "moving."]
    assert [w["start"] for w in out] == [0.0, 0.4, 0.8, 1.1]
    assert [w["end"] for w in out] == [0.4, 0.8, 1.1, 1.5]


def test_the_day_garbled_as_w_day_recovers_script_text():
    line = "The day didn't give you one quiet moment to land."
    words = _tokens(
        [
            ("W", 9.44, 9.66),
            ("-day", 9.66, 9.90),
            ("didn't", 9.90, 10.14),
            ("give", 10.14, 10.32),
            ("you", 10.32, 10.54),
            ("one", 10.54, 10.76),
            ("quiet", 10.76, 11.02),
            ("moment", 11.02, 11.32),
            ("to", 11.32, 11.52),
            ("land.", 11.52, 11.84),
        ]
    )
    out = narration.align_words(line, words)
    assert [w["word"] for w in out] == line.split()
    by_word = {w["word"]: w for w in out}
    assert by_word["day"]["start"] == 9.66
    assert by_word["day"]["end"] == 9.90
    # equal word counts zip positionally: "The" keeps the "W" token's timing,
    # which is exactly when it was actually spoken
    assert by_word["The"]["start"] == 9.44
    assert by_word["The"]["end"] == 9.66
    starts = [w["start"] for w in out]
    assert starts == sorted(starts)


def test_every_with_leading_w_garbage_and_split_word():
    line = "Every late-night scroll is a search for soothing."
    words = _tokens(
        [
            ("W.", 14.94, 15.58),
            ("Every", 15.58, 15.74),
            ("late", 15.74, 15.96),
            ("night", 15.96, 16.20),
            ("scroll", 16.20, 16.46),
            ("is", 16.46, 16.68),
            ("a", 16.68, 16.90),
            ("search", 16.90, 17.04),
            ("for", 17.04, 17.14),
            ("soothing.", 17.14, 17.34),
        ]
    )
    out = narration.align_words(line, words)
    assert [w["word"] for w in out] == line.split()
    by_word = {w["word"]: w for w in out}
    assert by_word["Every"]["start"] == 15.58
    assert by_word["late-night"]["start"] == 15.74
    assert by_word["late-night"]["end"] == 16.20


def test_2am_split_into_two_tokens_merges():
    line = "Your 2am scroll isn't weakness."
    words = _tokens(
        [
            ("Your", 0.0, 0.38),
            ("2", 0.38, 0.58),
            ("AM", 0.58, 0.82),
            ("scroll", 0.82, 1.14),
            ("isn't", 1.14, 1.38),
            ("weakness,", 1.38, 1.66),
        ]
    )
    out = narration.align_words(line, words)
    assert [w["word"] for w in out] == line.split()
    by_word = {w["word"]: w for w in out}
    assert by_word["2am"]["start"] == 0.38
    assert by_word["2am"]["end"] == 0.82


def test_hyphenated_word_from_two_tokens():
    line = "It's self-preservation."
    words = _tokens(
        [
            ("It's", 0.0, 0.4),
            ("self", 0.4, 0.7),
            ("-preservation.", 0.7, 1.0),
        ]
    )
    out = narration.align_words(line, words)
    assert [w["word"] for w in out] == ["It's", "self-preservation."]
    assert out[1]["start"] == 0.4
    assert out[1]["end"] == 1.0


def test_pipe_and_em_dash_never_surface_in_captions():
    line = "Racing. | Your body isn't avoiding your life—it's trying to feel safe."
    words = _tokens(
        [
            ("Racing.", 0.0, 0.5),
            ("Your", 0.5, 0.9),
            ("body", 0.9, 1.2),
            ("isn't", 1.2, 1.5),
            ("avoiding", 1.5, 1.9),
            ("your", 1.9, 2.2),
            ("life,", 2.2, 2.5),
            ("it's", 2.5, 2.8),
            ("trying", 2.8, 3.1),
            ("to", 3.1, 3.3),
            ("feel", 3.3, 3.5),
            ("safe.", 3.5, 3.8),
        ]
    )
    out = narration.align_words(line, words)
    expected = [w for w in line.split() if any(ch.isalnum() for ch in w)]
    assert [w["word"] for w in out] == expected
    assert all("|" not in w["word"] for w in out)
    by_word = {w["word"]: w for w in out}
    assert by_word["life—it's"]["start"] == 2.2
    assert by_word["life—it's"]["end"] == 2.8


def test_missing_word_midline_is_interpolated():
    line = "a b c d e"
    words = _tokens([("a", 0.0, 0.5), ("c", 0.7, 1.0), ("e", 1.4, 1.7)])
    out = narration.align_words(line, words)
    assert [w["word"] for w in out] == ["a", "b", "c", "d", "e"]
    assert out[0]["start"] == 0.0
    assert out[1]["start"] == 0.5
    assert out[1]["end"] == 0.7
    assert out[2]["start"] == 0.7
    assert out[3]["start"] == 1.0
    assert out[3]["end"] == 1.4
    assert out[4]["end"] == 1.7


def test_fully_garbled_line_falls_back_to_even_timing():
    line = "Every so now you're not failing."
    words = _tokens(
        [
            ("W.", 0.0, 0.5),
            ("So", 0.5, 0.9),
            ("now", 0.9, 1.2),
            ("you're", 1.2, 1.5),
            ("not", 1.5, 1.7),
            ("failing.", 1.7, 1.9),
        ]
    )
    out = narration.align_words(line, words)
    assert [w["word"] for w in out] == line.split()
    assert out[0]["start"] == 0.0
    assert out[-1]["end"] == 1.9
    starts = [w["start"] for w in out]
    assert starts == sorted(starts)
    # last word's start is interpolated from the line end, not the gap
    assert out[0]["end"] == out[1]["start"]


def test_no_tokens_uses_duration():
    out = narration.align_words("one two three", [], 3.0)
    assert [w["word"] for w in out] == ["one", "two", "three"]
    assert [w["start"] for w in out] == [0.0, 1.0, 2.0]
    assert [w["end"] for w in out] == [1.0, 2.0, 3.0]


def test_empty_script_returns_empty():
    assert narration.align_words("", _tokens([("hi", 0.0, 0.1)])) == []
    assert narration.align_words("", []) == []


def test_leading_garbage_tokens_are_skipped():
    line = "The day was long."
    words = _tokens(
        [
            ("///", 0.0, 0.3),
            ("W", 0.3, 0.5),
            ("-day", 0.5, 0.7),
            ("was", 0.7, 0.9),
            ("long.", 0.9, 1.2),
        ]
    )
    out = narration.align_words(line, words)
    assert [w["word"] for w in out] == line.split()
    by_word = {w["word"]: w for w in out}
    assert by_word["day"]["start"] == 0.5
    assert by_word["day"]["end"] == 0.7


def test_timings_stay_monotonic_and_non_negative():
    line = "One two three four five"
    words = _tokens([("one", 0.0, 0.2), ("two", 0.2, 0.4), ("five", 0.8, 1.0)])
    out = narration.align_words(line, words)
    assert [w["word"] for w in out] == line.split()
    assert all(w["start"] >= 0.0 for w in out)
    assert all(w["start"] <= w["end"] for w in out)


@pytest.mark.asyncio
async def test_synthesize_narration_returns_script_words(monkeypatch):
    line = "The day didn't give you one quiet moment to land."
    raw = _tokens(
        [
            ("W", 9.44, 9.66),
            ("-day", 9.66, 9.90),
            ("didn't", 9.90, 10.14),
            ("give", 10.14, 10.32),
            ("you", 10.32, 10.54),
            ("one", 10.54, 10.76),
            ("quiet", 10.76, 11.02),
            ("moment", 11.02, 11.32),
            ("to", 11.32, 11.52),
            ("land.", 11.52, 11.84),
        ]
    )

    def fake_synthesize(lines, out_wavs, owner="", voice_preset=""):
        for p in out_wavs:
            with open(p, "wb") as f:
                f.write(b"dummy")

    def fake_transcribe(paths, owner=""):
        return [raw]

    def fake_duration(path):
        return 11.84

    monkeypatch.setattr(narration, "synthesize_batch", fake_synthesize)
    monkeypatch.setattr(narration, "transcribe_all", fake_transcribe)
    monkeypatch.setattr(narration, "get_duration", fake_duration)

    pipeline = ReelPipeline()
    (wav_path, duration, words) = (await pipeline._synthesize_narration([line]))[0]
    assert wav_path.endswith(".wav")
    assert duration == 11.84
    assert [w["word"] for w in words] == line.split()
    assert words[1]["start"] == 9.66


@pytest.mark.asyncio
async def test_section_holds_do_not_extend_wav_durations(monkeypatch):
    def fake_synthesize(lines, out_wavs, owner="", voice_preset=""):
        for p in out_wavs:
            with open(p, "wb") as f:
                f.write(b"dummy")

    def fake_transcribe(paths, owner=""):
        return [[] for _ in paths]

    monkeypatch.setattr(narration, "synthesize_batch", fake_synthesize)
    monkeypatch.setattr(narration, "transcribe_all", fake_transcribe)
    monkeypatch.setattr(narration, "get_duration", lambda path: 2.0)

    pipeline = ReelPipeline(render_config=RenderConfig(section_holds={"hook": 0.5}))
    line_data = await pipeline._synthesize_narration(["Hook."])
    assert [duration for _, duration, _ in line_data] == [2.0]


# ── Voice prosody presets ──────────────────────────────────────────────────────


def test_prepend_silence_builds_ffmpeg_concat_command(monkeypatch):
    captured = {}

    def fake_run_blocking(cmd, **kwargs):
        captured["cmd"] = cmd
        captured["kwargs"] = kwargs

    monkeypatch.setattr(narration.subprocess_guard, "run_blocking", fake_run_blocking)
    narration.prepend_silence("/tmp/line.wav", 0.5, "/tmp/padded.wav", owner="t")

    assert captured["cmd"][0] == "ffmpeg"
    assert captured["cmd"][1] == "-y"
    assert "anullsrc=channel_layout=stereo:sample_rate=44100:d=0.5" in captured["cmd"]
    assert any("[a0][a1]concat=n=2:v=0:a=1[a]" in arg for arg in captured["cmd"])
    assert captured["cmd"][-1] == "/tmp/padded.wav"
    assert captured["kwargs"]["timeout"] == 120
    assert captured["kwargs"]["label"] == "hook lead-in silence"


def test_voice_presets_cover_all_three_prosody_params():
    assert set(narration.VOICE_PRESETS) == {"natural", "dramatic", "energetic"}
    for preset in ("natural", "dramatic", "energetic"):
        exaggeration, cfg_weight, temperature = narration.VOICE_PRESETS[preset]
        assert 0.0 <= exaggeration <= 1.0
        assert 0.0 <= cfg_weight <= 1.0
        assert 0.0 <= temperature <= 1.0
    assert narration.DEFAULT_VOICE_PRESET == "natural"


def test_synthesize_batch_sends_preset_params_per_item(monkeypatch):
    import json as _json

    payload = {}

    def fake_run_blocking(cmd, **kwargs):
        payload["stdin"] = kwargs["input"]

    monkeypatch.setattr(narration.subprocess_guard, "run_blocking", fake_run_blocking)
    narration.synthesize_batch(
        ["Hello world.", "Second line."],
        ["/tmp/a.wav", "/tmp/b.wav"],
        owner="test",
        voice_preset="dramatic",
    )
    items = _json.loads(payload["stdin"])
    assert len(items) == 2
    for item in items:
        assert item["exaggeration"] == 0.7
        assert item["cfg_weight"] == 0.3
        assert item["temperature"] == 0.9


def test_synthesize_batch_unknown_preset_falls_back_to_natural(monkeypatch):
    import json as _json

    payload = {}

    def fake_run_blocking(cmd, **kwargs):
        payload["stdin"] = kwargs["input"]

    monkeypatch.setattr(narration.subprocess_guard, "run_blocking", fake_run_blocking)
    narration.synthesize_batch(["Hi."], ["/tmp/a.wav"], voice_preset="shouty")
    item = _json.loads(payload["stdin"])[0]
    assert item["exaggeration"] == 0.5
    assert item["cfg_weight"] == 0.5
    assert item["temperature"] == 0.85


@pytest.mark.asyncio
async def test_pipeline_forwards_voice_preset(monkeypatch):
    seen = {}

    def fake_synthesize(lines, out_wavs, owner="", voice_preset=""):
        seen["preset"] = voice_preset
        for p in out_wavs:
            with open(p, "wb") as f:
                f.write(b"dummy")

    def fake_transcribe(paths, owner=""):
        return [[] for _ in paths]

    def fake_duration(path):
        return 1.0

    monkeypatch.setattr(narration, "synthesize_batch", fake_synthesize)
    monkeypatch.setattr(narration, "transcribe_all", fake_transcribe)
    monkeypatch.setattr(narration, "get_duration", fake_duration)

    pipeline = ReelPipeline(voice_preset="energetic")
    await pipeline._synthesize_narration(["Hello."])
    assert seen["preset"] == "energetic"
    assert pipeline.voice_preset == "energetic"
    assert ReelPipeline().voice_preset == "natural"
    assert ReelPipeline(voice_preset="bogus").voice_preset == "natural"

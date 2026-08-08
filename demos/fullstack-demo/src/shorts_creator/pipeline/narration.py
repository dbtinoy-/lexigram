"""Local narration synthesis (Chatterbox TTS) + word-level timing (Whisper).

Chatterbox renders each script line to a WAV file entirely offline; Whisper
then re-transcribes that same WAV to recover real per-word start/end
timestamps. This is what lets word-synced captions track the actual spoken
audio instead of the LLM's estimated section durations.

Whisper's transcription *text* is never trusted: the tiny models routinely
garble this TTS voice ("The day" -> "W-day", "Every" -> "W. Every"), so
captions are built from the script's own words and Whisper only supplies
timings, realigned onto the script text by `align_words`.

Chatterbox lives in its own venv (chatterbox-venv, Python 3.11 + torch,
~3.6GB of weights) instead of the app venv. The worker is invoked once per
pipeline run and synthesizes every line in a single process so the model is
loaded once rather than once per line.
"""

import json
import os
import shutil
import struct

from shorts_creator.pipeline import subprocess_guard

_DSM_DIR = os.path.dirname(__file__)
_DSM_PARENT = os.path.abspath(os.path.join(_DSM_DIR, "..", "..", "..", ".."))
_FALLBACK_VENV = os.path.join(
    os.path.dirname(_DSM_PARENT), "dsm", "chatterbox-venv", "bin", "python3"
)
_CHATTERBOX_VENV_CANDIDATES = [
    os.path.join(_DSM_PARENT, "chatterbox-venv", "bin", "python3"),
    _FALLBACK_VENV,
]
CHATTERBOX_VENV_PYTHON = next(
    (p for p in _CHATTERBOX_VENV_CANDIDATES if os.path.exists(p)),
    _CHATTERBOX_VENV_CANDIDATES[0],
)
CHATTERBOX_WORKER = os.path.join(_DSM_DIR, "_chatterbox_worker.py")

_WHISPER_LOCAL = os.path.expanduser("~/.local/bin/whisper")
WHISPER_BIN = (
    shutil.which("whisper")
    or (_WHISPER_LOCAL if os.path.exists(_WHISPER_LOCAL) else None)
    or os.path.join(os.path.dirname(CHATTERBOX_VENV_PYTHON), "whisper")
)
WHISPER_MODEL = "tiny.en"

# Per-voice Chatterbox prosody presets: (exaggeration, cfg_weight, temperature).
# "natural" is Chatterbox's documented "general use" baseline - the previous
# umbrella use of the "dramatic" combo (0.7/0.3) pushed prosody hard enough
# to read as strained/robotic on this voice. The temperature values are
# nudged from Chatterbox's default (0.8) for a bit more natural pitch/pacing
# variation between lines instead of a flat, uniform delivery.
VOICE_PRESETS = {
    "natural": (0.5, 0.5, 0.85),
    "dramatic": (0.7, 0.3, 0.9),
    "energetic": (0.6, 0.4, 0.95),
}
DEFAULT_VOICE_PRESET = "natural"


def synthesize_batch(
    lines: list[str], out_wavs: list[str], owner: str = "", voice_preset: str = DEFAULT_VOICE_PRESET
) -> None:
    """Render each of `lines` to its matching path in `out_wavs` via
    Chatterbox, loading the model once for the whole batch. Unknown preset
    names fall back to the natural baseline.
    """
    exaggeration, cfg_weight, temperature = VOICE_PRESETS.get(
        voice_preset, VOICE_PRESETS[DEFAULT_VOICE_PRESET]
    )
    items = [
        {
            "text": line,
            "out_wav": out_wav,
            "exaggeration": exaggeration,
            "cfg_weight": cfg_weight,
            "temperature": temperature,
        }
        for line, out_wav in zip(lines, out_wavs)
    ]
    subprocess_guard.run_blocking(
        [CHATTERBOX_VENV_PYTHON, CHATTERBOX_WORKER],
        input=json.dumps(items),
        timeout=600,
        label="Chatterbox TTS",
        owner=owner,
    )


def transcribe_all(wav_paths: list[str], owner: str = "") -> list[list[dict]]:
    """Word timings for every wav, sequentially in the calling thread."""
    return [get_word_timings(wav_path, owner=owner) for wav_path in wav_paths]


def prepend_silence(wav_path: str, seconds: float, out_path: str, owner: str = "") -> None:
    """Prepend `seconds` of silence to a wav via ffmpeg concat."""
    subprocess_guard.run_blocking(
        [
            "ffmpeg",
            "-y",
            "-f",
            "lavfi",
            "-i",
            f"anullsrc=channel_layout=stereo:sample_rate=44100:d={seconds}",
            "-i",
            wav_path,
            "-filter_complex",
            ("[0:a]aresample=44100[a0];[1:a]aresample=44100[a1];[a0][a1]concat=n=2:v=0:a=1[a]"),
            "-map",
            "[a]",
            "-ar",
            "44100",
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            out_path,
        ],
        timeout=120,
        label="hook lead-in silence",
        owner=owner,
    )


def get_duration(wav_path: str) -> float:
    with open(wav_path, "rb") as f:
        data = f.read()
    if len(data) < 44:
        return 0.0
    # Walk RIFF chunks to find the "data" chunk — some WAV writers
    # insert extra chunks (fact, PEAK, etc.) between fmt and data.
    channels = struct.unpack_from("<H", data, 22)[0]
    sample_rate = struct.unpack_from("<I", data, 24)[0]
    byte_rate = struct.unpack_from("<I", data, 28)[0]
    pos = 12  # skip RIFF header
    data_size = 0
    while pos < len(data):
        chunk_id = data[pos : pos + 4]
        if len(chunk_id) < 4:
            break
        chunk_size = struct.unpack_from("<I", data, pos + 4)[0]
        if chunk_id == b"data":
            data_size = chunk_size
            break
        pos += 8 + chunk_size
        if pos % 2:
            pos += 1
    if byte_rate > 0:
        return data_size / byte_rate
    if channels == 0 or sample_rate == 0:
        return 0.0
    bits_per_sample = struct.unpack_from("<H", data, 34)[0]
    return data_size / (channels * (bits_per_sample / 8) * sample_rate)


def get_word_timings(wav_path: str, owner: str = "") -> list[dict]:
    """Return [{"word": str, "start": float, "end": float}, ...] via Whisper,
    relative to the start of `wav_path`. Empty list if Whisper finds no words
    (e.g. a very short clip) - callers should fall back to a single caption
    spanning the whole line.

    The "word" texts are Whisper's own transcription and must NOT be used for
    on-screen captions - feed the results through `align_words` first.
    """
    out_dir = os.path.dirname(wav_path) or "."
    base = os.path.splitext(os.path.basename(wav_path))[0]
    subprocess_guard.run_blocking(
        [
            WHISPER_BIN,
            wav_path,
            "--model",
            WHISPER_MODEL,
            "--word_timestamps",
            "True",
            "--output_format",
            "json",
            "--output_dir",
            out_dir,
            "--language",
            "en",
            # CPU-only: tiny.en is fast on a short line, and running on CUDA
            # while Chatterbox is mid-batch contends for the same GPU (which
            # has previously wedged the pipeline).
            "--device",
            "cpu",
        ],
        timeout=300,
        label=f"Whisper timings for {base}",
        owner=owner,
    )
    json_path = os.path.join(out_dir, f"{base}.json")
    with open(json_path) as f:
        data = json.load(f)
    words: list[dict] = []
    for segment in data.get("segments", []):
        for w in segment.get("words", []):
            text = w["word"].strip()
            if not text:
                continue
            # Whisper sometimes splits one written word into two word-timestamp
            # entries with no space between them (e.g. "push" then "-ups,"
            # for "pushups") - merge the continuation into the previous entry
            # so downstream caption grouping never breaks a single word apart.
            if words and not w["word"].startswith(" "):
                words[-1]["word"] += text
                words[-1]["end"] = w["end"]
            else:
                words.append({"word": text, "start": w["start"], "end": w["end"]})
    return words


_ALNUM = set("abcdefghijklmnopqrstuvwxyz0123456789")
_MAX_RUN = 3


def _normalize_token(text: str) -> str:
    """Lowercase and strip every non-alphanumeric character.

    Punctuation, apostrophes and hyphens are dropped entirely so "didn't"
    matches "didn't", "self-preservation." matches "self" + "-preservation.",
    "life—it's" matches "life" + "it's", and "2am" matches "2" + "AM".
    """
    return "".join(ch for ch in text.lower() if ch in _ALNUM)


def _script_words(text: str) -> list[str]:
    """The tokens of a script line, dropping non-word glue like pipes and
    standalone hyphens ("Racing. | Your body..." -> ["Racing.", "Your", ...]).
    """
    return [w for w in text.split() if any(ch.isalnum() for ch in w)]


def _even_timing(script_words: list[str], line_end: float) -> list[dict]:
    """Fallback: spread every script word evenly across [0, line_end]."""
    n = len(script_words)
    if n == 0:
        return []
    if line_end <= 0 or n == 1:
        return [{"word": w, "start": 0.0, "end": line_end} for w in script_words]
    width = line_end / n
    return [
        {"word": w, "start": i * width, "end": (i + 1) * width} for i, w in enumerate(script_words)
    ]


def align_words(script_text: str, words: list[dict], duration: float | None = None) -> list[dict]:
    """Return the script's own words with Whisper-derived start/end timings.

    Whisper transcribes the TTS voice poorly at small model sizes ("The day"
    -> "W" "-day", "Every" -> "W." "Every") and splits one written word into
    several tokens ("2am" -> "2" "AM", "self-preservation." -> "self"
    "-preservation."), so the raw transcription can't be used as caption text
    and its timings need realigning. A dynamic-programming alignment maps each
    script word to the run of 1-3 Whisper tokens that cover it (tokens that
    fuse must match the written word - "late"+"night" for "late-night");
    any script word Whisper never heard (e.g. "The" at line start) is
    interpolated between the surrounding matched words' timings.

    Returns one dict per script word: {"word": <script text>, "start",
    "end"}. `duration` is used only as the line end when `words` is empty.
    """
    script_words = _script_words(script_text)
    if not script_words:
        return []
    if not words:
        return _even_timing(script_words, duration or 0.0)
    if len(script_words) == len(words):
        return [
            {"word": script_words[i], "start": words[i]["start"], "end": words[i]["end"]}
            for i in range(len(script_words))
        ]

    n, m = len(script_words), len(words)
    norm_script = [_normalize_token(w) for w in script_words]

    # dp[i][j]: best score for the suffix script_words[i:] vs words[j:].
    # Matching a script word to k fused tokens scores +2; skipping either
    # side scores -1. Ties prefer matches (strict >).
    dp = [[0] * (m + 1) for _ in range(n + 1)]
    back: list[list[tuple[str, int] | None]] = [[None] * (m + 1) for _ in range(n + 1)]
    for i in range(n):
        dp[i][m] = -(n - i)
        back[i][m] = ("skip_word", 0)
    for j in range(m):
        dp[n][j] = -(m - j)
        back[n][j] = ("skip_token", 0)
    for i in range(n - 1, -1, -1):
        for j in range(m - 1, -1, -1):
            best = -(10**9)
            choice = None
            for k in range(1, _MAX_RUN + 1):
                if j + k <= m:
                    fused = "".join(words[j + x]["word"].strip() for x in range(k))
                    if _normalize_token(fused) == norm_script[i]:
                        score = dp[i + 1][j + k] + 2
                        if score > best:
                            best, choice = score, ("match", k)
            if dp[i + 1][j] - 1 > best:
                best, choice = dp[i + 1][j] - 1, ("skip_word", 0)
            if dp[i][j + 1] - 1 > best:
                best, choice = dp[i][j + 1] - 1, ("skip_token", 0)
            dp[i][j], back[i][j] = best, choice

    spans: list[tuple[int, int] | None] = [None] * n
    i = j = 0
    while i < n and j < m:
        entry = back[i][j]
        if entry is None:
            break
        tag, arg = entry
        if tag == "match":
            spans[i] = (j, j + arg - 1)
            i += 1
            j += arg
        elif tag == "skip_word":
            i += 1
        else:
            j += 1

    aligned: list[dict | None] = [None] * n
    for idx, span in enumerate(spans):
        if span is not None:
            t0, t1 = span
            aligned[idx] = {
                "word": script_words[idx],
                "start": words[t0]["start"],
                "end": words[t1]["end"],
            }

    # Interpolate script words with no Whisper match between their neighbors.
    line_end = words[-1]["end"] or (duration or 0.0)
    run_start = 0
    while run_start < n:
        if aligned[run_start] is not None:
            run_start += 1
            continue
        run_end = run_start
        while run_end < n and aligned[run_end] is None:
            run_end += 1
        prev = aligned[run_start - 1] if run_start > 0 else None
        nxt = aligned[run_end] if run_end < n else None
        prev_end = prev["end"] if prev is not None else 0.0
        next_start = nxt["start"] if nxt is not None else line_end
        width = max(0.0, (next_start - prev_end) / (run_end - run_start))
        for k in range(run_end - run_start):
            start = prev_end + width * k
            aligned[run_start + k] = {
                "word": script_words[run_start + k],
                "start": start,
                "end": start + width,
            }
        run_start = run_end

    for item in aligned:
        if item is None:
            continue
        item["end"] = max(item["end"], item["start"])
    return [item for item in aligned if item is not None]

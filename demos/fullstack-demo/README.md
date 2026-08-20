# shorts-creator

End-to-end short-video reel generator: LLM script generation (hook / message /
metaphor / conclusion), Chatterbox TTS narration with per-line prosody presets,
Whisper word timings, mood-keyed stock background segments, caption + hook
overlay rendering, and ffmpeg compose.

## Prerequisites

- `ffmpeg` / `ffprobe` on PATH
- Stock API keys in `.env`: `PIXABAY_API_KEY`, `PEXELS_API_KEY`
- `whisper` CLI (`~/.local/bin/whisper`) for word timings
- Chatterbox TTS runtime venv (see below) — narration falls back to a bundled
  sample clip without it

## Chatterbox TTS venv

The pipeline resolves `CHATTERBOX_VENV_PYTHON` from
`narration.CHATTERBOX_VENV_CANDIDATES`. Point it at a Python 3.11+ venv with
`chatterbox-tts` and its dependencies installed (the default candidates list
includes a local `chatterbox-venv`). That venv was lost once and rebuilt as
follows (network to PyPI is flaky; most wheels come from the local uv cache or
the pytorch index):

```sh
/usr/bin/python3.12 -m venv --system-site-packages ./chatterbox-venv
```

Notes:

- Use the system `python3.12`, NOT a uv-managed `python3.12` on PATH
  (broken `/install` prefix — `init_fs_encoding` fails) — adjust the path if
  your system Python lives elsewhere.
- System user-site supplies `torch 2.4.0+cu124`, `numba 0.66`, `numpy 1.26.4`,
  `transformers`, `diffusers` — then install into the venv:

```sh
venv/bin/pip install --retries 25 --timeout 180 \
  torchaudio==2.4.0+cu124 --index-url https://download.pytorch.org/whl/cu124
uv pip install --python venv/bin/python --offline --no-deps \
  chatterbox-tts==0.1.7 transformers==5.2.0 diffusers==0.29.0 librosa==0.11.0 \
  einops s3tokenizer pykakasi==2.3.0 omegaconf pyloudnorm conformer==0.3.2
venv/bin/pip install --retries 25 --timeout 180 \
  lazy_loader 'huggingface-hub>=1.3.0,<2.0' soxr onnx pooch soundfile \
  audioread resampy resemble-perth onnxruntime 'antlr4-python3-runtime==4.9.3' \
  numpy==1.26.4
```
(Replace `venv` with the actual venv path.)

Pitfalls encountered:

- `torchaudio` from PyPI is the cu121 build and fails against `torch +cu124`
  ("compiled with different CUDA versions") — use the cu124 index.
- `onnx` pulls `numpy 2.x` which breaks user-site numba — reinstall
  `numpy==1.26.4` last to shadow it.
- `omegaconf` needs `antlr4-python3-runtime==4.9.3` (ATN version 3); 4.12+
  fails with "Could not deserialize ATN".
- `resemble-perth` needs `onnxruntime`, else
  `perth.PerthImplicitWatermarker` is `None` and `ChatterboxTTS()` raises
  `'NoneType' object is not callable`.
- TTS weights are cached at
  `~/.cache/huggingface/hub/models--ResembleAI--chatterbox` (no re-download);
  use `HF_HUB_OFFLINE=1` for smoke tests.

## Tests

Use `uv run python -m pytest` — the `.venv/bin/pytest` shebang points at the
`5.creators` mirror copy and runs a stale codebase.

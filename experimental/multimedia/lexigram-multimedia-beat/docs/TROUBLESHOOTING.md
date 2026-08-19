# Troubleshooting

Common issues with `lexigram-multimedia-beat` and how to fix them.

---

## Problem: ImportError for `librosa` or `soundfile`

**Error:** `ModuleNotFoundError: No module named 'librosa'` when the provider registers,
or a crash inside `LibrosaBeatAnalysisProvider._analyze_sync`.

**Cause:** The `librosa` in-process backend is an optional extra; the base install does not
ship it.

**Solution:** Install the extra:

```bash
uv add "lexigram-multimedia-beat[librosa]"
```

---

## Problem: `ProviderNotInstalledError` for an unknown backend

**Error:** `ProviderNotInstalledError: Unknown or unimplemented beat-analysis backend: 'foo'`

**Cause:** `BeatAnalysisConfig.backend` holds a value other than the two supported ones
(`"librosa"`, `"madmom"`). `BeatAnalysisGenerationProvider.register()` raises eagerly.

**Solution:** Use a supported backend.

```python
from lexigram.multimedia.beat.config import BeatAnalysisConfig

config = BeatAnalysisConfig(backend="librosa")  # or "madmom"
```

```yaml
multimedia_beat:
  backend: "madmom"
```

---

## Problem: madmom server unreachable / connection error

**Error:** `Err(MultimediaError("Madmom request failed: ..."))` from `analyze()`, or
`aiohttp.ClientConnectorError` in logs.

**Cause 1:** The `lexigram-beat-madmom-serve` process is not running, or it is bound to a
different host/port than `config.madmom_base_url`.

**Solution:**

```bash
pip install "lexigram-multimedia-beat[madmom-server]"
lexigram-beat-madmom-serve   # listens on :5600 by default
curl http://localhost:5600/health   # expect {"status":"ok"}
```

**Cause 2:** `timeout` is too low for the model (default `30.0`), so slow requests time out.

**Solution:** Raise the timeout.

```yaml
multimedia_beat:
  timeout: 60.0
```

---

## Problem: decode failure on the librosa backend

**Error:** `BeatAnalysisDecodeError: librosa could not decode audio: ...`
(`LEX_ERR_MM_BEAT_003`).

**Cause:** The asset bytes are not a decodable audio container (wrong format, truncated
data, or a URI that downloaded an error page). The backend materializes the asset to a temp
file and lets `librosa.load()` decode it.

**Solution:** Verify the asset carries real audio bytes (or a fetchable URI) with a valid
`mime_type`. If you pass a URI, ensure it resolves to the audio stream, not an error page:

```python
from lexigram.contracts.multimedia.types import MediaAsset

asset = MediaAsset(mime_type="audio/mp3", provider="storage", uri="https://cdn/real-audio.mp3")
```

Debug by decoding the same bytes yourself first (`librosa.load(path)` in a REPL).

---

## Problem: `analyze()` hangs or blocks the event loop

**Symptom:** Requests stall during beat detection on CPU-heavy audio.

**Cause:** The librosa beat tracker (`librosa.beat.beat_track`) is CPU-bound; it must not
block the event loop. This is normally handled by `asyncio.to_thread`.

**Solution:** Confirm you are calling the provider through the async `analyze()` method
(which shells out to a thread), not invoking `_analyze_sync()` directly. For very long
clips, pre-trim the audio to the section you actually need before analysis.

---

## Problem: health check reports DEGRADED for madmom

**Symptom:** `BeatAnalysisGenerationProvider.health_check()` returns `DEGRADED`, or the
umbrella's aggregate health shows the `beat` component degraded.

**Cause:** For `madmom`, health probes `GET {madmom_base_url}/health`. A non-200 response
or a timeout/connection error yields `DEGRADED`. The model may also be reported as
`loading` right after server startup.

**Solution:** Confirm the server is up and healthy, then re-check:

```bash
curl http://localhost:5600/health   # "ok" once the model is loaded
```

Wait a moment after starting the server — the model loads in the `on_startup` handler, so
the very first requests can hit the `loading` state. The `librosa` backend never probes the
network and reports `HEALTHY` whenever it constructed successfully.

---

## Debug Tips

- Set `LOG_LEVEL=DEBUG`; the provider logs `beat_analysis_registered` with the chosen
  `backend` at `register()`.
- Resolve `BeatAnalysisProvider` and inspect its type: it should be
  `LibrosaBeatAnalysisProvider` or `MadmomBeatAnalysisProvider` matching `config.backend`.
- Wrap `analyze()` in `try/except` around `aiohttp` calls only for *unexpected* failures;
  expected ones already arrive as `Err(MultimediaError)` values.
- Use `BeatAnalysisModule.stub()` in tests — it forces `librosa` and avoids all networking.
- If a submitted asset came from `normalize_asset_dict`, it will be URI-backed (no bytes);
  `MadmomBeatAnalysisProvider` base64-encodes bytes, so fetch the URI to bytes first when
  using the madmom path on a normalized asset.

---

## Still Stuck?

- Read the [Guide](./GUIDE.md) for the two-backend mental model.
- See [Configuration](./CONFIGURATION.md) for backend/timeout/URL knobs.
- Open an issue at https://github.com/dbtinoy-/lexigram/issues
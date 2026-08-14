# How-To Guides

Task-oriented recipes for `lexigram-multimedia-beat`.

---

## Analyze an Audio Asset (librosa, in-process)

```python
from lexigram.contracts.multimedia.types import BeatAnalysisRequest, MediaAsset
from lexigram.multimedia.beat import BeatAnalysisModule


app.add_module(BeatAnalysisModule.configure())
await app.start()

beat = await app.container.resolve(BeatAnalysisProvider)

result = await beat.analyze(
    BeatAnalysisRequest(asset=MediaAsset(mime_type="audio/wav", provider="local", bytes_data=audio))
)
if result.is_ok():
    analysis = result.unwrap()
    print(f"{analysis.tempo_bpm:.1f} bpm across {len(analysis.beat_timestamps)} beats")
```

`LibrosaBeatAnalysisProvider` materializes `bytes_data` (or downloads `asset.uri`),
runs `librosa.beat.beat_track` in a worker thread, and returns
`Ok(BeatAnalysisResult(tempo_bpm=..., beat_timestamps=[...]))`.

---

## Start the Madmom Reference Server

```bash
pip install "lexigram-multimedia-beat[madmom-server]"
lexigram-beat-madmom-serve
```

Starts aiohttp on port `5600`:

- `POST /analyze` — expects `{"audio_bytes": "<base64>"}`, returns
  `{"tempo_bpm": float, "beat_timestamps": [float, ...]}`.
- `GET /health` — `{"status": "ok"}` once the model is loaded.

The server loads `madmom.features.beats.RNNBeatProcessor()` once in `on_startup` and reuses
it for every request; `DBNBeatTrackingProcessor(fps=100)` converts activations to beat
timestamps, and tempo is derived from inter-beat intervals.

---

## Analyze via the Madmom Backend

```python
from lexigram.multimedia.beat import BeatAnalysisModule
from lexigram.multimedia.beat.config import BeatAnalysisConfig


app.add_module(
    BeatAnalysisModule.configure(
        config=BeatAnalysisConfig(backend="madmom", madmom_base_url="http://localhost:5600")
    )
)
await app.start()

beat = await app.container.resolve(BeatAnalysisProvider)  # MadmomBeatAnalysisProvider
result = await beat.analyze(BeatAnalysisRequest(asset=asset))
```

`MadmomBeatAnalysisProvider.analyze()` base64-encodes `asset.bytes_data`, posts it to
`{base_url}/analyze` with a timeout from `config.timeout`, and parses the JSON response.
Non-200 responses return `Err(MultimediaError("Madmom server returned {status}: ..."))`.

---

## Add Retry and a Circuit Breaker

Bind `RetryPolicyProtocol` and `CircuitBreakerProtocol` before the beat provider boots;
the madmom backend picks them up automatically during `register()`:

```python
from lexigram.resilience import ResilienceModule

app.add_module(ResilienceModule.configure())  # binds RetryPolicyProtocol + CircuitBreakerProtocol
app.add_module(BeatAnalysisModule.configure(config=BeatAnalysisConfig(backend="madmom")))
```

The provider calls `await resolve_optional(container, ...)` for both protocols — when
present, calls are wrapped as `retry.execute(circuit_breaker.call, self._post, payload)`
(or each alone if only one is bound); when absent, requests go out raw. Tune retry/breaker
behavior through `ResilienceConfig` (sections `retry:` and `circuit_breaker:`).

---

## Drive Beat-Synced Video Cuts

Use the timestamps to schedule `lexigram-multimedia-video` processing via the umbrella:

```python
from lexigram.contracts.multimedia import BeatAnalysisRequest, MusicRequest
from lexigram.multimedia import MultimediaModule


app.add_module(MultimediaModule.configure())
await app.start()

provider = next(p for p in app.providers if p.name == "multimedia")

mix = await provider.music.generate(MusicRequest(prompt="dark techno, 128 bpm", duration_seconds=60.0))
analysis = (await provider.beat.analyze(BeatAnalysisRequest(asset=mix.unwrap()))).unwrap()
cut_points = analysis.beat_timestamps

for i, (start, end) in enumerate(zip(cut_points, cut_points[1:])):
    await provider.video.submit_process(
        Trim(asset=footage, start=start, end=end),
        idempotency_key=f"beat-cut-{i}",
    )
```

This is the canonical workflow: beat analysis (sync) → queued video cuts (async).

---

## Handle Decode Failures Explicitly

```python
from lexigram.multimedia.beat import BeatAnalysisModule
from lexigram.multimedia.beat.exceptions import BeatAnalysisDecodeError


app.add_module(BeatAnalysisModule.configure())
await app.start()

beat = await app.container.resolve(BeatAnalysisProvider)

result = await beat.analyze(BeatAnalysisRequest(asset=broken_asset))
if result.is_err():
    err = result.unwrap_err()
    if isinstance(err, BeatAnalysisDecodeError):
        print("librosa could not decode the audio:", err)
    else:
        print("other failure:", err)
```

`BeatAnalysisDecodeError` (`LEX_ERR_MM_BEAT_003`) extends
`BeatAnalysisError` (`LEX_ERR_MM_008` from contracts) which extends `MultimediaError` —
catch progressively wider types for layered handling.

---

## Notes

- The `librosa` backend constructs with no I/O and reports `HEALTHY` without any network
  probe; the madmom backend probes `{madmom_base_url}/health` during
  `BeatAnalysisGenerationProvider.health_check()` and reports `DEGRADED` on timeouts or
  non-200 responses.
- Assets with neither bytes nor URI produce an HTTP GET failure or a decode error,
  depending on backend — always populate one of the two.
- `BeatAnalysisModule.stub()` forces `BeatAnalysisConfig(backend="librosa")`, so tests
  never need the server.
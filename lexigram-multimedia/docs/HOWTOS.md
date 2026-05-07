# How-To Guides

Task-oriented recipes for `lexigram-multimedia`. Each uses real classes from the source.

---

## Generate and Download TTS Audio

```python
from lexigram.contracts.multimedia import TTSProvider, TTSRequest

tts: TTSProvider = await app.container.resolve(TTSProvider)
result = await tts.generate(TTSRequest(text="Welcome to the show", voice="alloy", format="mp3"))

if result.is_ok():
    asset = result.unwrap()
    if asset.has_bytes:
        with open("voice.mp3", "wb") as f:
            f.write(asset.bytes_data)
    elif asset.has_uri:
        print(asset.uri)
```

`TTSRequest` carries `text`, optional `voice`, `format`, `reference_audio_uri`, and
`emotion`. Backend-specific work is delegated to the configured provider.

---

## Generate Background Music With Caching

Enable result caching so repeated prompts short-circuit the backend:

```python
from lexigram.contracts.multimedia import MusicProvider, MusicRequest
from lexigram.multimedia import MultimediaConfig, MultimediaModule

app.add_module(
    MultimediaModule.configure(config=MultimediaConfig(cache_results=True)),
)
await app.start()

music = await app.container.resolve(MusicProvider)
for _ in range(10):
    result = await music.generate(MusicRequest(prompt="upbeat summer house", duration_seconds=30.0))
    if result.is_ok():
        print(result.unwrap().uri)   # only the first call hits the backend
```

The cache key is the canonical-JSON + sha256 digest of the request, namespaced as
`multimedia:music_generation:{digest}`.

---

## Process a Video (trim + subtitle burn)

```python
from lexigram.multimedia import MultimediaModule
from lexigram.contracts.multimedia import BurnSubtitles, SubtitleCue, Trim, VideoRequest

app.add_module(MultimediaModule.configure())
await app.start()

provider = next(p for p in app.providers if p.name == "multimedia")
video = provider.video

# Generation
gen = await video.generate(VideoRequest(prompt="a cat on a skateboard", duration_seconds=6.0))
if gen.is_ok():
    clip = gen.unwrap()

    # Processing
    trimmed = await video.process(Trim(asset=clip, start=0.5, end=5.0))
    if trimmed.is_ok():
        captioned = await video.process(
            BurnSubtitles(
                asset=trimmed.unwrap(),
                cues=[SubtitleCue(start=0.0, end=2.0, text="Here comes the cat")],
            )
        )
        print(captioned.unwrap().uri)
```

`VideoAccessor.process()` runs ffmpeg-backed operations; `VideoAccessor.submit_process()`
queues the same work with idempotency.

---

## Submit an Async Generation Job and Poll

```python
from lexigram.multimedia import MultimediaModule
from lexigram.contracts.multimedia import ImageRequest

app.add_module(MultimediaModule.configure())
await app.start()

provider = next(p for p in app.providers if p.name == "multimedia")
handle = await provider.image.submit(
    ImageRequest(prompt="a serene mountain lake at dusk", width=1024, height=1024),
    idempotency_key="lake-poster",
)
print(f"job_id={handle.job_id} status={handle.status} duplicate={handle.is_duplicate}")

# Resubmitting the same key returns a duplicate handle and does not re-enqueue:
again = await provider.image.submit(
    ImageRequest(prompt="a serene mountain lake at dusk", width=1024, height=1024),
    idempotency_key="lake-poster",
)
print(again.is_duplicate)  # True if still tracked
```

The `JobHandle.is_duplicate` flag is accurate when the umbrella owns the `IdempotencyManager`
(its default) — it pre-checks the idempotency store before submitting.

---

## Compose a Timeline to Video

```python
from lexigram.multimedia import MultimediaModule, Timeline
from lexigram.contracts.multimedia import MediaAsset, EncodeSpec, TransitionSpec

app.add_module(MultimediaModule.configure())
provider = next(p for p in app.providers if p.name == "multimedia")

timeline = Timeline()
timeline.add_clip(clip_a, transition_in=TransitionSpec(kind="crossfade", duration=0.5))
timeline.add_clip(clip_b, transition_in=TransitionSpec(kind="crossfade", duration=0.5))
timeline.set_narration(voice_over)
timeline.set_music(bgm, duck_under_narration=True)
timeline.add_captions([SubtitleCue(start=0.0, end=3.0, text="Chapter one")])
timeline.set_encode(EncodeSpec(codec="libx264", resolution="1080p", fps=30))

result = await provider.compose.render(timeline)
if result.is_ok():
    composed = result.unwrap()
    print(composed.uri)

# Or queue it:
handle = await provider.compose.submit_render(timeline, idempotency_key="sizzle-reel")
```

`ComposeAccessor.render()` drives `Timeline.render()` through the video `VideoProcessor`;
`submit_render()` first normalizes in-memory assets to storage, then queues.

---

## Run Beat Analysis to Time Your Cuts

```python
from lexigram.contracts.multimedia import BeatAnalysisRequest

provider = next(p for p in app.providers if p.name == "multimedia")
result = await provider.beat.analyze(BeatAnalysisRequest(asset=mix))
if result.is_ok():
    analysis = result.unwrap()
    print("tempo_bpm", analysis.tempo_bpm)
    print("n_beats", len(analysis.beat_timestamps))
    # Align video cuts to the strongest beats
    cuts = [max(analysis.beat_timestamps, key=lambda t: abs(t - c)) for c in candidate_cut_times]
```

`BeatAccessor.analyze()` is sync-only by design — it returns a `BeatAnalysisResult`
(`tempo_bpm` + `beat_timestamps`), a pure value with nothing to persist, so there is no
queued path.

---

## Upscale or Interpolate a Whole Video

```python
provider = next(p for p in app.providers if p.name == "multimedia")

hi_res = await provider.video.upscale_video(source, scale_factor=4)
smooth = await provider.video.interpolate_video(source, factor=2, fps=60.0)

if hi_res.is_ok():
    print(hi_res.unwrap().uri)
else:
    # Err(ProviderNotInstalledError) when no VideoProcessor is configured
    print("Whole-video upscale unavailable:", hi_res.unwrap_err())
```

Both require a `VideoProcessor` configured in the sibling subsystem; otherwise they return
`Err(ProviderNotInstalledError)` rather than raising.

---

## Notes

- The **protocol-level** path (`resolve(TTSProvider)`) returns a raw backend; the
  **accessor-level** path (`MultimediaProvider.video`, `.image`, …) adds storage, caching,
  events, and idempotent submission.
- Submit-based handlers are only wired when `lexigram-tasks` is bound; otherwise `submit()`
  raises because no `TaskQueueProtocol` is registered.
- Result caching applies only when `cache_results: true` **and** a cache backend is bound.
- Generation events publish only when an `EventBusProtocol` is bound.
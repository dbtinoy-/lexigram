# How-To Guides

Task-oriented recipes for `lexigram-multimedia-video`.

---

## Generate a Video from Text

```python
from lexigram.contracts.multimedia import VideoProvider, VideoRequest

video = await app.container.resolve(VideoProvider)
result = await video.generate(
    VideoRequest(prompt="a calm ocean at golden hour", duration_seconds=6.0)
)
if result.is_ok():
    asset = result.unwrap()  # MediaAsset — bytes or uri
```

The default `local-http` backend POSTs `{prompt, duration_seconds, resolution, image_uri, format}` to `POST /generate`.

---

## Animate an Image (First-Frame → Video)

```python
result = await video.generate(
    VideoRequest(
        prompt="the lighthouse animates as waves crash",
        image_uri="https://cdn.example.com/lighthouse.jpg",
        duration_seconds=8.0,
    )
)
```

Wan2.2 and the local HTTP server honor `image_uri`; SVD (and ComfyUI) **require** it; CogVideoX lets the server decide.

---

## Reference-Driven Generation via OpenAI Gateway

```python
from lexigram.contracts.multimedia import VideoMode, VideoRequest

result = await video.generate(
    VideoRequest(
        prompt="two actors on a stage",
        mode=VideoMode.MULTIMODAL_REFERENCE,
        reference_images=["https://cdn.example.com/a.png", "https://cdn.example.com/b.png"],
        reference_videos=["https://cdn.example.com/ref.mp4"],
        generate_audio=True,
        ratio="16:9",
        seed=42,
    )
)
```

`OpenAIVideoProvider` builds the Seedance/HuiMeng-gateway payload (`first_frame_image`, `last_frame_image`, `reference_images` ≤ 9, `reference_videos` ≤ 3, `reference_audios` ≤ 3). Request-shape problems (e.g. missing `image_uri` for `first_frame`) return `Err(VideoGenerationError)`, not a crash.

---

## Trim a Clip

```python
from lexigram.contracts.multimedia import MediaAsset, Trim

out = await processor.process(
    Trim(
        asset=MediaAsset(mime_type="video/mp4", provider="local",
                         uri="file:///tmp/clip.mp4"),
        start=1.0,
        end=4.0,
    )
)  # Ok(MediaAsset) — stream copies (-c copy), no re-encode
```

---

## Concat Clips with a Crossfade

```python
from lexigram.contracts.multimedia import Concat, MediaAsset, TransitionSpec

out = await processor.process(
    Concat(
        assets=[
            MediaAsset(..., uri="file:///tmp/a.mp4"),
            MediaAsset(..., uri="file:///tmp/b.mp4"),
            MediaAsset(..., uri="file:///tmp/c.mp4"),
        ],
        transitions=[
            TransitionSpec(kind="crossfade", duration=0.5),
            TransitionSpec(kind="crossfade", duration=0.3),
        ],
    )
)
```

Crossfades render as an `xfade`/`acrossfade` chain; `TransitionSpec(kind="cut")` (or omitted) renders as an instant cut expressed as a minimal-duration `xfade`. Clip durations are probed automatically via ffprobe for crossfade concats.

---

## Overlay Text (Watermark / Caption)

```python
from lexigram.contracts.multimedia import OverlayText

out = await processor.process(
    OverlayText(
        asset=clip,
        text="Lexigram",
        position="bottom-right",     # top/bottom/center/top-left/top-right/bottom-left/bottom-right
        font_size=28,
        color="white",
        start=0.5,
        end=3.5,                     # enable window: between(t, 0.5, 3.5)
    )
)
```

---

## Overlay an Image (Logo / Lower Third)

```python
from lexigram.contracts.multimedia import OverlayImage

out = await processor.process(
    OverlayImage(
        asset=clip,
        image_asset=MediaAsset(mime_type="image/png", provider="local", bytes_data=logo_png),
        position="top-left",
        opacity=0.8,                 # < 1.0 applies colorchannelmixer alpha
    )
)  # -filter_complex overlay, maps [v] + best audio
```

---

## Compose a Multi-Layer Edit with Fades and Audio

```python
from lexigram.contracts.multimedia import (
    ComposeAudioLayer,
    ComposeLayer,
    ComposeVideo,
    EncodeSpec,
    MediaAsset,
)

out = await processor.process(
    ComposeVideo(
        asset=base,                                    # output duration == base
        layers=[
            ComposeLayer(asset=overlay_a, start=1.0, end=5.0, fade_in=0.3, fade_out=0.3),
            ComposeLayer(asset=overlay_b, start=2.0, fade_in=0.2),   # end=None → to base end
        ],
        audio_layers=[ComposeAudioLayer(asset=music, start=0.0, volume=0.7)],
        fade_in=0.2,
        base_fade_out=0.75,                            # base fades to black before end
        encode=EncodeSpec(codec="libx264", bitrate="8M", resolution="1920x1080", fps=30),
    )
)
```

Layers overlay in list order on `[start, end)` windows with per-layer fades; audio layers are delayed/volume-scaled and `amix`-ed; the base's audio is dropped unless audio layers are present. A no-op `ComposeVideo` (no layers/audio/fades/encode) short-circuits to a plain copy.

---

## Burn Subtitles Into a Clip

```python
from lexigram.contracts.multimedia import BurnSubtitles, SubtitleCue

out = await processor.process(
    BurnSubtitles(
        asset=clip,
        cues=[
            SubtitleCue(start=0.5, end=2.5, text="Hello, world"),
            SubtitleCue(start=3.0, end=5.0, text="Second line"),
        ],
    )
)
```

The processor writes an SRT (via `cues_to_srt`) and passes it to the `subtitles=` filter.

---

## Mux a Music Track

```python
from lexigram.contracts.multimedia import MediaAsset, MuxAudio

# replace entirely:
out = await processor.process(MuxAudio(asset=clip, audio_asset=music, mode="replace"))

# mix with ducking (music lowered while the existing narration is present):
out = await processor.process(
    MuxAudio(asset=clip, audio_asset=music, mode="mix",
             music_volume=0.8, duck_under_existing=True)
)  # sidechaincompress ducking
```

---

## Extract a Thumbnail

```python
from lexigram.contracts.multimedia import ExtractThumbnail

out = await processor.process(
    ExtractThumbnail(asset=clip, timestamp=3.0)
)  # MediaAsset provider="ffmpeg", mime_type="image/png"
```

---

## Export a GIF

```python
from lexigram.contracts.multimedia import ToGif

out = await processor.process(
    ToGif(asset=clip, start=0.0, end=3.0, fps=12, width=480)
)  # mime_type="image/gif"
```

---

## Transcode / Re-Encode

```python
from lexigram.contracts.multimedia import Transcode

out = await processor.process(
    Transcode(asset=clip, format="mov", codec="libx264", resolution="1280x720", bitrate="4M")
)  # suffix + mime follow format
```

---

## Change Speed

```python
from lexigram.contracts.multimedia import ChangeSpeed

out = await processor.process(
    ChangeSpeed(asset=clip, factor=2.0)
)  # setpts=0.5*PTS on video, atempo=2.0 on audio
```

---

## Crop

```python
from lexigram.contracts.multimedia import Crop

out = await processor.process(
    Crop(asset=clip, x=100, y=50, width=1280, height=720)
)  # -vf crop=width:height:x:y
```

---

## Apply a Color Filter

```python
from lexigram.contracts.multimedia import ColorFilter

out = await processor.process(
    ColorFilter(asset=clip, preset="sepia")
)  # presets: grayscale, sepia, vintage (or none + brightness/contrast/saturation)
```

---

## Run a Raw ffmpeg Filter Graph

```python
from lexigram.contracts.multimedia import MediaAsset, RawFilter

out = await processor.process(
    RawFilter(
        assets=[clip, overlay],
        filter_complex="[0:v][1:v]blend=all_mode=screen[v]",
        maps=["[v]"],
        extra_args=["-c:v", "libx264"],
    )
)
```

`RawFilter` is the escape hatch: pass any `-filter_complex`, `-map` list, and extra trailing args.

---

## Extract and Reassemble Frames (Pipelines)

```python
frames = await processor.extract_frames(clip)
# Ok(list[MediaAsset]) — each "image/png", metadata["source_fps"] set

rebuilt = await processor.assemble_frames(frames.unwrap(), fps=30.0)
# Ok(MediaAsset) — sequential frame%06d input reassembled to video/mp4
```

This is exactly the pipeline `VideoUpscaleService` (from `lexigram-multimedia-upscale`) uses to enlarge a whole video frame-by-frame.

---

## Report Progress

```python
out = await processor.process(
    ToGif(asset=clip, width=640),
    progress_callback=lambda pct: print(f"{(pct * 100):.0f}%"),
)
```

Passed a callback, the processor parses ffmpeg's `-progress pipe:1` output and emits `0.0 → 1.0` throttled updates (≥1% deltas, `1.0` once on success).

---

## Process by Async-Job Params (lexigram-tasks)

```python
result = await processing_task.run(
    {
        "operation_type": "ComposeVideo",
        "asset": {"mime_type": "video/mp4", "provider": "local", "uri": "file:///tmp/b.mp4"},
        "layers": [
            {
                "asset": {"mime_type": "video/quicktime", "provider": "local",
                          "uri": "file:///tmp/l.mov"},
                "start": 1.0, "end": None, "fade_in": 0.0, "fade_out": 0.0,
            }
        ],
        "audio_layers": [],
        "fade_in": 0.0, "fade_out": 0.0, "base_fade_out": 0.75,
        "encode": {"codec": "hevc_nvenc", "bitrate": "10M", "resolution": "1080x1920", "fps": 30},
    }
)  # {"provider", "mime_type", "bytes_data", "uri", "metadata"}
```

`operation_type` equals the operation's class name; nested assets are rebuilt with `_asset_from_params`. Generation params follow the same pattern via `VideoGenerationTask.run(...)`.

---

## Use a Custom ComfyUI Workflow

```python
from lexigram.multimedia.video.config import VideoProcessingConfig, VideoConfig
from lexigram.multimedia.video import VideoModule

module = VideoModule.configure(
    config=VideoConfig(
        backend="comfyui",
        comfyui_base_url="http://localhost:8188",
        comfyui_checkpoint="svd_xt_1_1.safetensors",
        comfyui_workflow_path="/srv/workflows/my_svd.json",   # custom template
        comfyui_fps=8,
        comfyui_motion_bucket_id=127,
        comfyui_poll_interval=1.0,
    )
)
```

`ComfyUiVideoProvider` fills placeholders (`__IMAGE_PATH__`, `__CHECKPOINT__`, `__FPS__`, `__MOTION_BUCKET_ID__`, `__SEED__`) into the workflow template, POSTs it to `/prompt`, polls `/history/{prompt_id}` (fails fast on `status_str="error"` or an `execution_error` message), then fetches the output via `/view`. `request.image_uri` must be a path the ComfyUI process can reach.

---

## Notes

- All `process()`/`extract_frames()`/`assemble_frames()` work in a temp workdir cleaned up in a `finally` block; results are read into memory before it is removed.
- Concurrency is bounded by `VideoProcessingConfig.max_concurrent_jobs` (a semaphore); jobs past the limit wait.
- A `processing.timeout` expiry kills the ffmpeg process and returns `Err(VideoProcessingError("ffmpeg timed out ..."))`.
- `shutil.which()` gates processor registration — no `ffmpeg`, no `VideoProcessor`/`VideoProcessingTask` in the container.
- Generation timeouts differ by backend default (`local-http`/`runway`/`openai` 60s, `wan22`/`cogvideox` 180s, `svd`/`comfyui` 120s) unless `VideoConfig.timeout` is set.
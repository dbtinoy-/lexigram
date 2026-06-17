# Troubleshooting

Common issues with `lexigram-multimedia-video` and how to fix them.

---

## `video_processing_disabled` warning / `VideoProcessor` not resolvable

**Cause:** `VideoGenerationProvider.register()` ran `shutil.which()` on `processing.ffmpeg_binary` and found nothing. Without ffmpeg, neither `VideoProcessor` nor `VideoProcessingTask` is bound.

**Fix:** Install ffmpeg and confirm resolution:

```bash
which ffmpeg    # e.g. /usr/bin/ffmpeg
```

Or point the config at a binary:

```yaml
multimedia:
  video:
    processing:
      ffmpeg_binary: "/usr/local/bin/ffmpeg"
```

Then `await app.container.resolve(VideoProcessor)` works.

---

## ffmpeg job fails: `VideoProcessingError: ffmpeg error: ...`

**Cause:** The ffmpeg subprocess exited non-zero; the processor embeds ffmpeg's stderr in the error.

**Fix:** Re-run the equivalent command manually to inspect the filter graph:

```bash
ffmpeg -y -i input.mp4 -vf "drawtext=text='x':fontsize=28:fontcolor=white:x=(w-text_w)/2:y=20" out.mp4
```

Common root causes:

- Unknown codec / filters (verify your ffmpeg build includes `drawtext`, `xfade`, `subtitles`, etc.).
- Invalid `filter_complex` syntax in `RawFilter`.
- Input files not readable by the ffmpeg process account.

---

## `ValueError: clip_durations is required for crossfade concat`

**Cause:** A `Concat` operation has a `transition.kind == "crossfade"`, and the processor needs each clip's duration to compute `xfade` offsets — but probing failed or was skipped.

**Fix:** Ensure all input clips are real media files (not empty/zero-byte assets). The processor probes durations automatically in `_prepare()` for crossfade concats; if a probe returns junk, check the clip's integrity:

```bash
ffprobe -v error -show_entries format=duration -of default=noprint_wrappers=1:nokey=1 clip.mp4
```

---

## `ValueError` from `ComposeVideo` fades (`requires base_duration` / `layer fade_out requires end or layer_durations`)

**Cause:** `build_compose_argv` needs the base duration when `fade_out`/`base_fade_out` are set, and the layer's end (or a probed duration) when a layer has a `fade_out` but no `end`.

**Fix:**

- Keep `fade_out > 0` only on real compositions — the processor probes the base duration automatically before building the graph.
- For layer fades, always set `end` on the layer (or ensure the probe can read the layer clip):

```python
ComposeLayer(asset=clip, start=1.0, end=5.0, fade_out=0.5)
```

---

## Crossfade concat truncates the following clip

**Symptom:** The second clip is mostly missing after a crossfade at an exact segment boundary.

**Cause:** Known ffmpeg behavior: an `xfade`/`acrossfade` `offset` landing exactly at the end of the preceding segment silently truncates the chain. The code guards hard cuts with a `1/30 s` epsilon (`_CUT_DURATION`), but operator errors (e.g. overlapping transition windows you authored) can still trigger edge cases.

**Fix:** Verify transition math — `offset = cumulative - duration` assumes transitions shorter than the accumulated duration; keep `TransitionSpec(duration=...)` well below clip lengths. Test the pair in isolation first.

---

## `ProviderNotInstalledError: Unknown or unimplemented video backend`

**Cause:** `VideoConfig.backend` is not one of `local-http`, `runway`, `openai`, `wan22`, `cogvideox`, `svd`, `comfyui`.

**Fix:**

```python
VideoConfig(backend="svd")
```

---

## `VideoGenerationAuthenticationError` (401) with Runway / OpenAI

**Cause:** The `Authorization: Bearer <key>` request was rejected. Either the key is wrong, or it was never resolved — `resolve_credential` found nothing, so `api_key=""` was passed.

**Fix:** Store the key under the configured secret name and verify:

```python
# Secret store must contain a credential named:
VideoConfig().runway_api_key_secret_name   # "runway_api_key"
VideoConfig().openai_api_key_secret_name   # "openai_api_key"
```

If the credential resolves, `health_check()` reports `HEALTHY` immediately after boot (it reports `DEGRADED` otherwise).

---

## `VideoTimeoutError: ... did not complete within the poll budget`

**Cause:** The backend did not finish within its poll budget — `max_polls` × `poll_interval` (Runway/OpenAI: 60 × 3 s ≈ 180 s) or the ComfyUI history poll window (`comfyui` timeout, default 120 s).

**Fix:**

- Set `VideoConfig.timeout` for more headroom (forwarded to backends that accept it).
- Check the vendor console for a failed/cancelled job.
- For ComfyUI, confirm the prompt is actually queued: `curl <comfyui_base_url>/queue`.

---

## ComfyUI: `VideoGenerationError: ComfyUI execution failed` or fetch errors

**Cause:**

1. The workflow errored — `_has_execution_error` detected an `execution_error` message, or `status_str == "error"`.
2. `request.image_uri` is not a path the ComfyUI process can read.
3. The output node family isn't VHS (`gifs`/`videos`) or standard (`images`) — `_extract_output_file` expects one of these keys.

**Fix:**

- Check the ComfyUI UI/history for the prompt error.
- Serve the image with a URI ComfyUI can resolve (it is never base64-inlined).
- For custom-node output shapes, vendoring a custom workflow whose VHS node emits `gifs`/`videos` solves (3).

---

## SVD returns `Err(VideoGenerationError)` requiring `image_uri`

**Cause:** `SVDVideoProvider` deliberately returns an error when `image_uri` is missing — SVD has no text-to-video path and ignoring `prompt` is documented behavior.

**Fix:** Always supply the frame:

```python
VideoRequest(prompt="", image_uri="https://cdn.example.com/frame.png")
```

---

## `LocalHttpVideoProvider` rejects a hypothetical JSON response

**Error:** `local-http video server returned non-object JSON: ...` or `missing url: ...`

**Cause:** `local-http` accepts two response shapes — raw media bytes (default) or JSON `{"url": "..."}` — and this server returned something else.

**Fix:** Make the local server conform: return raw bytes with a media `Content-Type`, or a single-object `{"url": "..."} ` JSON body.

---

## Generation results are `uri`-only MediaAssets

**Cause:** By design, cloud/local backends often return a hosted URL rather than inlining large videos (`RunwayVideoProvider`, `OpenAIVideoProvider`, `LocalHttpVideoProvider`/`Wan22VideoProvider`/`CogVideoXVideoProvider`/`SVDVideoProvider` JSON responses).

**Fix:** Handle both shapes at the call site:

```python
if asset.has_uri:
    print("download:", asset.uri)
else:
    print("bytes:", len(asset.bytes_data or b""))
```

The task handlers return the same fields as a `dict`.

---

## Debug Tips

- Verify registration state:

```bash
export LOG_LEVEL=DEBUG   # provider logs "video_registered" with the backend
```

- Resolve and introspect:

```python
video = await app.container.resolve(VideoProvider)
print(type(video).__name__)            # e.g. LocalHttpVideoProvider
video_provider = next(p for p in app.providers if p.name == "video")
print(await video_provider.health_check())
```

- Run one-shot jobs with `VideoModule.stub()` + mocked backends to isolate supplier problems (see `tests/unit/`).
- Probe media independently with `ffprobe` before filing issues on the processor.

---

## Still Stuck?

- Confirm the backend server is up: `curl <base_url>/generate` should 404 (not refuse connection) on a healthy server.
- Re-read [Configuration](./CONFIGURATION.md) — most issues are a wrong base URL or a missing secret name.
- Open an issue at the `lexigram-multimedia-experimental` repository with the backend, the exact error text (stderr included), and your `VideoConfig`.
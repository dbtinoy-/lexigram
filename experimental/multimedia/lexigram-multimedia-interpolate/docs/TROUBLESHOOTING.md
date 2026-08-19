# Troubleshooting

Common issues and fixes for `lexigram-multimedia-interpolate`.

---

## Problem: `ProviderNotInstalledError` at boot — unknown backend

**Error:**

```
ProviderNotInstalledError: Unknown or unimplemented interpolation backend: 'foo'
```

**Cause:** `InterpolationConfig.backend` is not `"rife"` — the only implemented
backend.

**Solution:** Use the implemented value:

```python
from lexigram.multimedia.interpolate.config import InterpolationConfig

config = InterpolationConfig(backend="rife")
```

---

## Problem: Request fails — nothing listening at the RIFE server URL

**Error:**

```
MultimediaError: RIFE request failed: <aiohttp.ClientConnectorError ...>
```

or a plain timeout:

```
MultimediaError: RIFE request failed: timeout
```

**Cause:** No server at `rife_base_url` (default `http://localhost:5500`), the
server never finished loading its model, or the URL is wrong.

**Solution:** Start the reference server and check health first:

```bash
pip install "lexigram-multimedia-interpolate[rife-server]"
lexigram-interpolate-rife-serve &
curl http://localhost:5500/health        # {"status": "ok" | "loading"}
```

Oversized/lackluster GPUs can make startup slow — give the model load time;
`"loading"` means requests will fail until the model is ready. Or re-point the
config at the real host:

```yaml
multimedia_interpolate:
  rife_base_url: "http://rife.internal:5500"
```

---

## Problem: Server process exits immediately

**Error:**

```
ModuleNotFoundError: No module named 'rife'
ImportError: No module named 'torch'
```

**Cause:** `rife_server.py` imports `RifeModel` and `torch` lazily inside
`on_startup`. The server needs the optional `[rife-server]` extra; RIFE also
has no single official PyPI distribution, so the import must match whatever
RIFE implementation you vendor.

**Solution:**

```bash
pip install "lexigram-multimedia-interpolate[rife-server]"
# verify the import used by the server
python -c "from rife import RifeModel; print(RifeModel)"
```

If the vendored RIFE package differs (different module name or API), adjust
`rife_server.py`'s import and `RifeModel(device=...)` call accordingly. The
client package itself never imports torch.

---

## Problem: Interpolated midpoint is garbage or empty

**Symptom:** A successful `Ok(MediaAsset)` whose bytes are nonsense, or the
server produced an unusable image.

**Cause:** `RifeInterpolationProvider` transports `frame_a.bytes_data or b""` —
a `MediaAsset` with only a `uri` (bytes already persisted to storage by the
umbrella) sends *empty* frame data with a successful status.

**Solution:** Only interpolate assets that still carry bytes; reload frame
bytes from storage first:

```python
assert frame_a.has_bytes and frame_b.has_bytes, "frames must carry bytes"
```

If frames cross a process boundary (e.g. job results), rehydrate via
`_asset_from_params`-style reconstruction before building
`InterpolationRequest`:

```python
from lexigram.contracts.multimedia.types import MediaAsset

frame = MediaAsset(
    mime_type=data["mime_type"],
    provider=data["provider"],
    bytes_data=data.get("bytes_data"),  # refetch from storage when None
    uri=data.get("uri"),
    metadata=data.get("metadata", {}),
)
```

---

## Problem: `VideoInterpolationService` cannot be resolved

**Error:**

```
ResolutionError: Cannot resolve VideoInterpolationService: not registered
```

**Cause:** `InterpolationGenerationProvider` registers the service only when a
`VideoProcessor` is present in the container (`resolve_optional`). Without it
(e.g. `lexigram-multimedia-video` not installed/registered), only
`InterpolationProvider` and `InterpolationTask` exist.

**Solution:** Register a `VideoProcessor` fulfillment alongside the
interpolation module:

```python
module = AppModule.imports([
    InterpolationModule.configure(),
    VideoModule.configure(),          # registers the ffmpeg-backed VideoProcessor
])
# or bind your own VideoProcessor-implementing singleton in a custom provider
```

---

## Problem: `interpolate_video` returns "empty frame list"

**Error:**

```
MultimediaError: extract_frames returned an empty frame list
```

**Cause:** `VideoProcessor.extract_frames(asset)` returned `Ok([])` — the input
video had no decodable frames.

**Solution:** Validate extraction before interpolating:

```python
frames = await video_processor.extract_frames(asset)
print(len(frames.unwrap_or([])))          # 0 → the source video is the problem
```

Check that the source `MediaAsset` holds valid video bytes (`mime_type` starts
with `video/`), the codec is supported by the ffmpeg-backed processor, and
`asset.has_bytes` is true.

---

## Problem: `interpolate_video` dominates request time

**Symptom:** Whole-video interpolation appears to hang or times out.

**Cause:** The default `timeout: 15.0` bounds each **individual** `/interpolate`
call — but a single doubling pass issues one call per frame pair, and `factor=4`
runs two passes. A 240-frame clip is 239 midpoint calls, then 477, then
reassembly.

**Solution:** Scope work by clip length, raise the config timeout, and monitor
progress:

```yaml
multimedia_interpolate:
  timeout: 60.0
```

Process clips in segments and reassemble the segments with
`video_processor.process(Concat(...))` rather than interpolating hour-long
files in one call.

---

## Debug Tips

- Enable debug logging — the provider logs `interpolation_registered` with the
  configured backend at registration.
- Probe `provider.health_check(timeout=5.0)` — `DEGRADED` pinpoints an
  unreachable server before you send real frames.
- `curl http://localhost:5500/health` and watch `"loading"` → `"ok"` to
  confirm startup completed.
- In tests, use `InterpolationModule.stub()` to exercise DI wiring without any
  server.

---

## Still Stuck?

- Re-check the three config fields in [Configuration](./CONFIGURATION.md) —
  `rife_base_url` mismatch is the most common root cause.
- Confirm which layer failed: the client (request error) vs the server
  process (import/startup error) vs storage (URI-only frames).
- Open an issue at
  https://github.com/dbtinoy-/lexigram/issues
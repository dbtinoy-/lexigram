# Troubleshooting: lexigram-multimedia-tts

Common issues with text-to-speech and how to fix them. Error text comes from the package source; identifiers cross-reference `src/lexigram/multimedia/tts/`.

---

## Problem: `TTSAuthenticationError: ElevenLabs rejected the API key`

**Cause:** The ElevenLabs API returned HTTP 401. The key resolved from the secrets backend (via `elevenlabs_api_key_secret_name`) is wrong, expired, or missing. This is an infrastructure error — `ElevenLabsTTSProvider` **raises** it, it is not returned in a `Result`.

**Solution:** Verify the secret value stored under the configured name:

```python
from lexigram.multimedia.tts.config import TTSConfig

config: TTSConfig = await app.container.resolve(TTSConfig)
print(config.elevenlabs_api_key_secret_name)   # e.g. "elevenlabs_api_key"
```

Store a valid key under that name in the secrets backend (e.g. `AS_API_KEY` style secret store) and restart. Same story for OpenAI (`openai_api_key_secret_name`, 401 → `TTSAuthenticationError`).

---

## Problem: `ProviderNotInstalledError: ... backend selected but its extra is not installed`

**Cause:** `backend="elevenlabs"` (or any SDK-gated backend) was selected, but the import of the provider module failed. The guard in `AudioTTSProvider.register()` converts that into an actionable install hint.

**Solution:**

```bash
uv add "lexigram-multimedia-tts[elevenlabs]"
# or openai:  uv add "lexigram-multimedia-tts[openai]"
```

---

## Problem: `ProviderNotInstalledError: TTSConfig.elevenlabs_voice_id is required when backend='elevenlabs'`

**Cause:** You switched to the ElevenLabs backend without setting a voice ID. The provider fails **eagerly at registration** — by design.

**Solution:**

```python
from lexigram.multimedia.tts import AudioTTSModule
from lexigram.multimedia.tts.config import TTSConfig

module = AudioTTSModule.configure(
    config=TTSConfig(backend="elevenlabs", elevenlabs_voice_id="21m00Tcm4TlvDq8ikWAM")
)
```

---

## Problem: `TTSError: F5-TTS requires reference_audio_uri` / `requires extra['reference_text']`

**Cause:** `F5TTSProvider` performs zero-shot voice cloning and will not run without a reference clip. Missing `reference_audio_uri` (or `extra["reference_text"]` — the transcript needed for alignment) is a request-shape problem, returned as `Err(TTSError)` — no crash, but always an error.

**Solution:** Provide both fields — the URI must be one the **server** can fetch (`http(s)://` or `file://`):

```python
from lexigram.contracts.multimedia.types import TTSRequest

request = TTSRequest(
    text="The clone speaks.",
    reference_audio_uri="https://cdn.example.com/ref.wav",  # or file:///…/ref.wav
    extra={"reference_text": "Original sentence from the reference clip."},
)
result = await tts.generate(request)
if result.is_ok():
    print("cloned voice OK")
```

---

## Problem: `TTSError: ... request failed: <ClientError>` (server unreachable)

**Cause:** The local model server isn't running, is on a different host/port, or the container can't reach it. Every backend wraps `aiohttp.ClientError`/`TimeoutError` in `Err(TTSError(...))`.

**Solution:** Start the matching server and confirm the URL matches config:

```bash
lexigram-tts-chatterbox-serve   # :5100
lexigram-tts-kokoro-serve       # :5101
lexigram-tts-f5-tts-serve       # :5102
lexigram-tts-piper-serve        # :5103
curl http://localhost:5100/health
```

```python
config: TTSConfig = await app.container.resolve(TTSConfig)
print(config.backend, config.chatterbox_base_url)
```

---

## Problem: Server started but `/generate` returns 404

**Cause:** The `POST {base_url}/generate` route doesn't exist on the target. `LocalHttpTTSProvider` accepts any conforming server, but it must implement the exact wire shape: `{text, voice, format}` posted to `/generate`, `audio/*` bytes back.

**Solution:** Log the error body — the provider includes the raw response bytes in the message:

```python
result = await tts.generate(TTSRequest(text="hi"))
if result.is_err():
    print(result.unwrap_err())  # e.g. 'local-http TTS server returned 404: b"...'
```

Check the server's router (`app.router.add_post("/generate", ...)`) and payload keys. The reference servers in `servers/` are the canonical implementation.

---

## Problem: Output bytes are WAV even though `format="mp3"` was requested

**Cause:** By design. Chatterbox, F5-TTS, Kokoro, and Piper always return native WAV — `request.format` is **accepted but ignored** (see each provider's docstring). `LocalHttpTTSProvider` uses whatever `Content-Type` the server sends (default `audio/mpeg`).

**Solution:** Trust `asset.mime_type` rather than the request format:

```python
asset = result.unwrap()
print(asset.mime_type, asset.provider)   # e.g. audio/wav chatterbox
```

If you need MP3, transcode downstream — or use a hosted backend (`elevenlabs`, `openai`), which return `audio/mpeg`.

---

## Problem: Health check says `DEGRADED` for a hosted backend with a valid key

**Cause:** `AudioTTSProvider.health_check()` for **API backends** (elevenlabs/openai) only verifies credential presence — `HEALTHY` if the key resolved, `DEGRADED` if absent. It deliberately **never makes a billed API call**. A `DEGRADED` status on a local backend means the `/health` probe failed (non-200, timeout, `aiohttp.ClientError`).

**Solution:**

```python
await provider.health_check(timeout=5.0)   # -> HealthCheckResult
```

- Local backend: `curl {base_url}/health` — expect `{"status": "ok"}` and HTTP 200.
- Hosted backend: confirm the secret resolves under `*_api_key_secret_name`; degraded means the key wasn't found at registration.

---

## Debug Tips

- Enable debug logging — the provider logs `tts_registered` with the chosen backend at registration.
- Read the live config back from the container: `await app.container.resolve(TTSConfig)` to confirm `backend` and every base URL.
- Test the wire shape directly with `curl -X POST {base_url}/generate -d '{"text":"hi"}' -H 'Content-Type: application/json'`.
- For hermetic tests use `AudioTTSModule.stub()` (pinned `local-http`) and mock the backend protocol for assertions (see the test suite under `tests/unit/`).

---

## Still Stuck?

- Review the config section: [Configuration](./CONFIGURATION.md)
- Trace the flow: [Architecture](./ARCHITECTURE.md)
- Check the [lexigram-multimedia-tts](https://github.com/dbtinoy-/lexigram) repository and open an issue with the backend name, full error text, and your server's `/health` response.
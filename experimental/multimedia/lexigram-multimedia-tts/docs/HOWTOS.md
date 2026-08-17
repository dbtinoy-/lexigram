# How-To Guides: lexigram-multimedia-tts

Task-oriented recipes for common TTS operations. All identifiers come from the source — `src/lexigram/multimedia/tts/`.

---

## Synthesize Speech with the Default Backend

`AudioTTSModule.configure()` with no arguments selects `backend="local-http"` (`LocalHttpTTSProvider` at `http://localhost:5002`).

```python
import asyncio

from lexigram import Application
from lexigram.contracts.multimedia import TTSProvider, TTSRequest
from lexigram.di.module import Module, module
from lexigram.multimedia.tts import AudioTTSModule


@module(imports=[AudioTTSModule.configure()])
class AppModule(Module):
    pass


async def main() -> None:
    async with Application.boot(modules=[AppModule]) as app:
        tts: TTSProvider = await app.container.resolve(TTSProvider)
        result = await tts.generate(TTSRequest(text="Bonjour le monde", voice="alloy"))
        if result.is_ok():
            asset = result.unwrap()
            with open("speech.mp3", "wb") as f:
                f.write(asset.bytes_data)  # type: ignore[arg-type]


asyncio.run(main())
```

---

## Use ElevenLabs (Hosted API)

Requires the ElevenLabs extra, a configured `elevenlabs_voice_id`, and an API key in the secrets backend.

```bash
uv add "lexigram-multimedia-tts[elevenlabs]"
```

```python
from lexigram.multimedia.tts import AudioTTSModule
from lexigram.multimedia.tts.config import TTSConfig

module = AudioTTSModule.configure(
    config=TTSConfig(
        backend="elevenlabs",
        elevenlabs_voice_id="21m00Tcm4TlvDq8ikWAM",
        elevenlabs_api_key_secret_name="elevenlabs_api_key",
    )
)
```

The provider resolves `elevenlabs_api_key` from the secrets store and POSTs to `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}` (see `_BASE_URL` in `providers/elevenlabs.py`). A 401 becomes `TTSAuthenticationError`.

```python
result = await tts.generate(TTSRequest(text="Hello from ElevenLabs"))
```

---

## Use Chatterbox (Local Model)

Chatterbox has a **single built-in voice** — `request.voice` is accepted for protocol compatibility but ignored. Output is always native WAV.

```bash
uv add "lexigram-multimedia-tts[chatterbox-server]"
lexigram-tts-chatterbox-serve          # serves :5100
```

```python
from lexigram.multimedia.tts import AudioTTSModule
from lexigram.multimedia.tts.config import TTSConfig

module = AudioTTSModule.configure(
    config=TTSConfig(
        backend="chatterbox",
        chatterbox_exaggeration=0.5,
        chatterbox_cfg_weight=0.5,
        chatterbox_temperature=0.85,
    )
)

result = await tts.generate(TTSRequest(text="This is the Chatterbox voice."))
```

---

## Clone a Voice with F5-TTS

Zero-shot cloning: pass a reference clip **as a URI the server fetches** plus its transcript.

```bash
uv add "lexigram-multimedia-tts[f5-tts-server]"
lexigram-tts-f5-tts-serve             # serves :5102
```

```python
request = TTSRequest(
    text="The cloned voice now speaks this line.",
    voice="any",  # ignored for cloning — F5-TTS blends reference + transcript
    reference_audio_uri="http://localhost:8000/ref.wav",
    extra={"reference_text": "Reference clip spoken transcript for alignment."},
)

result = await tts.generate(request)
```

`F5TTSProvider.generate()` returns `Err(TTSError(...))` if `reference_audio_uri` or `extra["reference_text"]` is missing — a request-shape error, never a crash.

---

## Use Piper (Lightest CPU Backend)

Piper is ONNX/CPU-only with sub-second cold start — great default for edge/CI.

```bash
uv add "lexigram-multimedia-tts[piper-server]"
lexigram-tts-piper-serve              # serves :5103
```

```python
config = TTSConfig(backend="piper", piper_default_voice="en_US-lessac-medium")
module = AudioTTSModule.configure(config=config)

result = await tts.generate(TTSRequest(text="Quick, low-latency speech."))
```

The server loads `PiperVoice.load(_DEFAULT_MODEL_PATH)` at startup and synthesizes per request.

---

## Run TTS in Tests (No Network / No Keys)

```python
import asyncio

from lexigram import Application
from lexigram.multimedia.tts import AudioTTSModule


async def test_boot():
    async with Application.boot(modules=[AudioTTSModule.stub()]) as app:
        assert app.container is not None
```

`AudioTTSModule.stub()` forces `TTSConfig(backend="local-http")`. For a hermetic unit test of the task wrapper, mock the backend protocol:

```python
from unittest.mock import AsyncMock
from lexigram.contracts.core.result import Ok
from lexigram.contracts.multimedia.types import MediaAsset, TTSRequest
from lexigram.multimedia.tts.tasks import TTSGenerationTask


def test_task_calls_backend() -> None:
    backend = AsyncMock()
    backend.generate.return_value = Ok(
        MediaAsset(mime_type="audio/mpeg", provider="openai", bytes_data=b"x")
    )
    task = TTSGenerationTask(backend=backend)
    # ... await task.run({"text": "hi", "voice": "alloy"})
```

---

## Handle Auth and Domain Errors Explicitly

Hosted backends surface credential problems as `TTSAuthenticationError` (raised) and everything else as `Err(TTSError)`:

```python
from lexigram.multimedia.tts.exceptions import TTSAuthenticationError
from lexigram.contracts.multimedia.exceptions import TTSError

try:
    result = await tts.generate(TTSRequest(text="hi", voice="alloy"))
except TTSAuthenticationError as exc:
    print(f"invalid credentials: {exc}")   # 401 from the API
else:
    if result.is_err():
        err = result.unwrap_err()
        assert isinstance(err, TTSError)
        print(f"generation failed: {err}")
```

---

## Notes

- **`format` is advisory on local backends** — Chatterbox, F5-TTS, Kokoro, Piper always return native WAV; `local-http` trusts the server's `Content-Type` (default `audio/mpeg`); hosted APIs return MP3.
- **API keys never touch config** — only `*_api_key_secret_name` appears in `TTSConfig`; the value is resolved from the secrets backend by name.
- **"accepted but ignored" is the contract** — e.g. `ChatterboxTTSProvider` swallows `request.voice` deliberately (single-voice model), mirroring how ACE-Step treats `tags`/`lyrics` in music.
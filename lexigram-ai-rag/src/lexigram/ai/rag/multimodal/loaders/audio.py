"""Audio loader for multi-modal RAG.

This module provides loading capabilities for audio documents with support for:
- Multiple formats: MP3, WAV, FLAC, OGG, AAC, M4A, WMA
- Audio metadata extraction (ID3 tags, etc.)
- Optional speech-to-text transcription
- Audio validation and normalization
"""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Any

from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)

try:
    import librosa

    # import soundfile as sf

    LIBROSA_AVAILABLE = True
except ImportError:
    LIBROSA_AVAILABLE = False

try:
    import mutagen

    MUTAGEN_AVAILABLE = True
except ImportError:
    MUTAGEN_AVAILABLE = False

import contextlib

from lexigram.ai.rag.exceptions import AudioLoaderError
from lexigram.ai.rag.multimodal.types import (
    AudioDocument,
    AudioFormat,
    AudioMetadata,
)


class AudioLoader:
    """Loader for audio documents.

    Supports loading audio from files or bytes with optional:
    - Metadata extraction (ID3, etc.)
    - Speech-to-text transcription
    - Format validation
    - Audio normalization

    Args:
        extract_metadata: Whether to extract audio metadata
        transcribe: Whether to transcribe audio to text
        sample_rate: Target sample rate (None to keep original)
        mono: Convert to mono audio
        normalize: Normalize audio volume

    Example:
        >>> loader = AudioLoader(transcribe=True)
        >>> doc = await loader.load("/path/to/audio.mp3")
        >>> print(doc.transcript)
        "Transcribed speech"
    """

    def __init__(
        self,
        extract_metadata: bool = True,
        transcribe: bool = False,
        sample_rate: int | None = None,
        mono: bool = False,
        normalize: bool = False,
    ):
        """Initialize audio loader."""
        if not LIBROSA_AVAILABLE:
            msg = "librosa and soundfile are required for audio loading. Install with: pip install librosa soundfile"
            raise ImportError(msg)

        self.extract_metadata = extract_metadata
        self.transcribe = transcribe
        self.sample_rate = sample_rate
        self.mono = mono
        self.normalize = normalize

        # Lazy load transcription model
        self._transcription_model = None

    async def load(
        self,
        source: str | Path | bytes,
        title: str | None = None,
        artist: str | None = None,
        **metadata_kwargs: Any,
    ) -> AudioDocument:
        """Load an audio document.

        Args:
            source: File path or raw bytes
            title: Optional audio title
            artist: Optional artist name
            **metadata_kwargs: Additional metadata fields

        Returns:
            AudioDocument with loaded audio data

        Raises:
            AudioLoaderError: If loading fails
        """
        try:
            # Load audio
            content: bytes | str
            if isinstance(source, (str, Path)):
                file_path = Path(source)
                exists = await asyncio.to_thread(file_path.exists)
                if not exists:
                    msg = f"Audio file not found: {source}"
                    raise AudioLoaderError(msg)

                # Load with librosa (Blocking I/O and CPU)
                def _load_librosa() -> Any:
                    return librosa.load(
                        str(file_path),
                        sr=self.sample_rate,
                        mono=self.mono,
                    )

                y, sr = await asyncio.to_thread(_load_librosa)
                content = str(file_path)

                # Detect format from file extension
                audio_format = self._detect_format(file_path)

            elif isinstance(source, bytes):
                # Load from bytes
                import io

                def _load_librosa_bytes() -> Any:
                    return librosa.load(
                        io.BytesIO(source),
                        sr=self.sample_rate,
                        mono=self.mono,
                    )

                y, sr = await asyncio.to_thread(_load_librosa_bytes)
                content = source
                file_path = None
                audio_format = AudioFormat.WAV  # Default for bytes

            else:
                msg = f"Unsupported source type: {type(source)}"
                raise AudioLoaderError(msg)

            # Normalize if requested (CPU intensive)
            if self.normalize:
                y = await asyncio.to_thread(librosa.util.normalize, y)

            # Get audio properties (CPU intensive)
            duration = await asyncio.to_thread(librosa.get_duration, y=y, sr=sr)
            channels = 1 if self.mono or y.ndim == 1 else y.shape[0]

            # Extract metadata (Blocking I/O)
            id3_data = {}
            if self.extract_metadata and file_path and MUTAGEN_AVAILABLE:
                id3_data = await asyncio.to_thread(self._extract_metadata, file_path)

            # Build metadata
            metadata = AudioMetadata(
                title=title or id3_data.get("title"),
                artist=artist or id3_data.get("artist"),
                album=id3_data.get("album"),
                genre=id3_data.get("genre"),
                year=id3_data.get("year"),
                id3=id3_data,
                **metadata_kwargs,
            )

            # Transcribe if requested (Already async/uses threads internally)
            transcript = None
            if self.transcribe:
                transcript = await self._transcribe_audio(y, sr)

            # Create document
            return AudioDocument(
                content=content,
                format=audio_format,
                duration=duration,
                sample_rate=sr,
                channels=channels,
                metadata=metadata,
                transcript=transcript,
                file_path=file_path,
            )

        except Exception as e:
            msg = f"Failed to load audio: {e}"
            raise AudioLoaderError(msg) from e

    async def load_batch(
        self,
        sources: list[str | Path | bytes],
        **kwargs: Any,
    ) -> list[AudioDocument]:
        """Load multiple audio files.

        Args:
            sources: List of audio sources
            **kwargs: Common metadata for all audio files

        Returns:
            List of loaded AudioDocuments
        """
        if not sources:
            return []

        async def _safe_load(source) -> Any:
            try:
                return await self.load(source, **kwargs)
            except AudioLoaderError as e:
                logger.warning("Failed to load audio %r: %s", source, e)
                return None

        tasks = [_safe_load(source) for source in sources]
        results = await asyncio.gather(*tasks)
        return [doc for doc in results if doc is not None]

    def _detect_format(self, file_path: Path) -> AudioFormat:
        """Detect audio format from file extension.

        Args:
            file_path: Path to audio file

        Returns:
            AudioFormat enum value
        """
        suffix = file_path.suffix.lower().lstrip(".")

        format_mapping = {
            "mp3": AudioFormat.MP3,
            "wav": AudioFormat.WAV,
            "flac": AudioFormat.FLAC,
            "ogg": AudioFormat.OGG,
            "aac": AudioFormat.AAC,
            "m4a": AudioFormat.M4A,
            "wma": AudioFormat.WMA,
        }

        if suffix not in format_mapping:
            msg = f"Unsupported audio format: {suffix}"
            raise AudioLoaderError(msg)

        return format_mapping[suffix]

    def _extract_metadata(self, file_path: Path) -> dict[str, Any]:
        """Extract metadata from audio file.

        Args:
            file_path: Path to audio file

        Returns:
            Dictionary of metadata
        """
        metadata: dict[str, Any] = {}

        try:
            audio_file = mutagen.File(str(file_path))
            if audio_file is not None:
                # Extract common tags
                if "title" in audio_file:
                    metadata["title"] = str(audio_file["title"][0])
                if "artist" in audio_file:
                    metadata["artist"] = str(audio_file["artist"][0])
                if "album" in audio_file:
                    metadata["album"] = str(audio_file["album"][0])
                if "genre" in audio_file:
                    metadata["genre"] = str(audio_file["genre"][0])
                if "date" in audio_file:
                    with contextlib.suppress(ValueError, IndexError):
                        metadata["year"] = int(str(audio_file["date"][0])[:4])

                # Store all tags
                metadata["all_tags"] = {k: str(v) for k, v in audio_file.items()}

        except (ValueError, TypeError, OSError, KeyError) as e:
            logger.warning("Failed to extract metadata: %s", e)

        return metadata

    async def _transcribe_audio(self, audio: Any, sample_rate: int) -> str:
        """Transcribe audio to text using OpenAI Whisper.

        Args:
            audio: Audio data array
            sample_rate: Sample rate

        Returns:
            Transcribed text
        """
        try:
            import whisper
        except ImportError:
            logger.warning("Whisper not installed. Skipping transcription.")
            return ""

        if self._transcription_model is None:
            # Load small model by default
            def _load() -> Any:
                return whisper.load_model("base")

            self._transcription_model = await asyncio.to_thread(_load)  # type: ignore[func-returns-value]

        # Transcribe
        model = self._transcription_model
        assert model is not None, "transcription model not loaded"

        def _transcribe() -> Any:
            result = model.transcribe(audio, fp16=False)
            return result.get("text", "").strip()

        return await asyncio.to_thread(_transcribe)

    def supports_transcription(self) -> bool:
        """Check if transcription is available.

        Returns:
            True if transcription model is loaded
        """
        return self._transcription_model is not None

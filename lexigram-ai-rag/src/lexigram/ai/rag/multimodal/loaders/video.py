"""Video loader for multi-modal RAG.

This module provides loading capabilities for video documents with support for:
- Multiple formats: MP4, AVI, MOV, MKV, FLV, WMV, WebM
- Key frame extraction
- Audio track extraction
- Video metadata extraction
- Optional transcription of audio track
"""

from __future__ import annotations

import asyncio
from pathlib import Path
import subprocess
from typing import Any

from lexigram.logging import (
    get_logger,
)

logger = get_logger(__name__)

try:
    import cv2  # type: ignore[import-not-found]
    import numpy as np

    CV2_AVAILABLE = True
except ImportError:
    cv2 = None
    np = None  # type: ignore[assignment]
    CV2_AVAILABLE = False

from lexigram.ai.rag.exceptions import VideoLoaderError
from lexigram.ai.rag.multimodal.loaders.audio import AudioLoader
from lexigram.ai.rag.multimodal.loaders.image import ImageLoader
from lexigram.ai.rag.multimodal.types import (
    AudioDocument,
    ImageDocument,
    VideoDocument,
    VideoFormat,
    VideoMetadata,
)


class VideoLoader:
    """Loader for video documents.

    Supports loading videos from files with:
    - Key frame extraction
    - Audio track extraction
    - Metadata extraction
    - Optional transcription

    Args:
        num_frames: Number of key frames to extract
        extract_audio: Whether to extract audio track
        transcribe_audio: Whether to transcribe audio
        frame_resize: Maximum dimension for extracted frames

    Example:
        >>> loader = VideoLoader(num_frames=10, extract_audio=True)
        >>> doc = await loader.load("/path/to/video.mp4")
        >>> print(len(doc.frames))
        10
    """

    def __init__(
        self,
        num_frames: int = 10,
        extract_audio: bool = True,
        transcribe_audio: bool = False,
        frame_resize: int | None = None,
    ):
        """Initialize video loader."""
        if not CV2_AVAILABLE:
            raise ImportError(
                "opencv-python is required for video loading. Install with: pip install opencv-python",
            )

        self.num_frames = num_frames
        self.extract_audio = extract_audio
        self.transcribe_audio = transcribe_audio
        self.frame_resize = frame_resize

        # Initialize sub-loaders
        self.image_loader = ImageLoader(
            extract_exif=False,
            extract_text=False,
            max_size=frame_resize,
        )

        if extract_audio:
            self.audio_loader = AudioLoader(
                extract_metadata=True,
                transcribe=transcribe_audio,
            )

    async def load(
        self,
        source: str | Path,
        title: str | None = None,
        description: str | None = None,
        **metadata_kwargs: Any,
    ) -> VideoDocument:
        """Load a video document.

        Args:
            source: File path to video
            title: Optional video title
            description: Optional description
            **metadata_kwargs: Additional metadata fields

        Returns:
            VideoDocument with loaded video data

        Raises:
            VideoLoaderError: If loading fails
        """
        try:
            # Validate file exists
            if isinstance(source, str | Path):
                file_path = Path(source)
                exists = await asyncio.to_thread(file_path.exists)
                if not exists:
                    msg = f"Video file not found: {source}"
                    raise VideoLoaderError(msg)
            else:
                raise VideoLoaderError(
                    "Only file paths are supported for video loading",
                )

            # Detect format (fast)
            video_format = self._detect_format(file_path)

            # Open video (I/O intensive)
            def _open_video() -> Any:
                return cv2.VideoCapture(str(file_path))

            cap = await asyncio.to_thread(_open_video)
            if not cap.isOpened():
                msg = f"Failed to open video file: {file_path}"
                raise VideoLoaderError(msg)

            # Get video properties (fast but safest in thread)
            def _get_props() -> Any:
                return {
                    "fps": cap.get(cv2.CAP_PROP_FPS),
                    "frame_count": int(cap.get(cv2.CAP_PROP_FRAME_COUNT)),
                    "width": int(cap.get(cv2.CAP_PROP_FRAME_WIDTH)),
                    "height": int(cap.get(cv2.CAP_PROP_FRAME_HEIGHT)),
                }

            props = await asyncio.to_thread(_get_props)
            fps = props["fps"]
            frame_count = props["frame_count"]
            width = props["width"]
            height = props["height"]
            duration = frame_count / fps if fps > 0 else 0

            # Extract key frames
            frames = await self._extract_frames(cap, frame_count)

            # Release video
            await asyncio.to_thread(cap.release)

            # Extract audio track
            audio_track = None
            transcript = None
            if self.extract_audio:
                try:
                    audio_track = await self._extract_audio(file_path)
                    if audio_track and audio_track.transcript:
                        transcript = audio_track.transcript
                except (
                    subprocess.SubprocessError,
                    FileNotFoundError,
                    OSError,
                    TimeoutError,
                ) as e:
                    logger.warning("Failed to extract audio: %s", e)

            # Build metadata
            metadata = VideoMetadata(
                title=title,
                description=description,
                **metadata_kwargs,
            )

            # Create document
            return VideoDocument(
                content=str(file_path),
                format=video_format,
                duration=duration,
                fps=fps,
                width=width,
                height=height,
                metadata=metadata,
                frames=frames,
                audio_track=audio_track,
                transcript=transcript,
                file_path=file_path,
            )

        except Exception as e:
            msg = f"Failed to load video {source}: {e}"
            raise VideoLoaderError(msg) from e

    async def load_batch(
        self,
        sources: list[str | Path],
        **kwargs: Any,
    ) -> list[VideoDocument]:
        """Load multiple video files.

        Args:
            sources: List of video sources
            **kwargs: Common metadata for all videos

        Returns:
            List of loaded VideoDocuments
        """
        if not sources:
            return []

        async def _safe_load(source) -> Any:
            try:
                return await self.load(source, **kwargs)
            except VideoLoaderError as e:
                logger.warning("Failed to load video %s: %s", source, e)
                return None

        tasks = [_safe_load(source) for source in sources]
        results = await asyncio.gather(*tasks)
        return [doc for doc in results if doc is not None]

    def _detect_format(self, file_path: Path) -> VideoFormat:
        """Detect video format from file extension.

        Args:
            file_path: Path to video file

        Returns:
            VideoFormat enum value
        """
        suffix = file_path.suffix.lower().lstrip(".")

        format_mapping = {
            "mp4": VideoFormat.MP4,
            "avi": VideoFormat.AVI,
            "mov": VideoFormat.MOV,
            "mkv": VideoFormat.MKV,
            "flv": VideoFormat.FLV,
            "wmv": VideoFormat.WMV,
            "webm": VideoFormat.WEBM,
        }

        if suffix not in format_mapping:
            msg = f"Unsupported video format: {suffix}"
            raise VideoLoaderError(msg)

        return format_mapping[suffix]

    async def _extract_frames(
        self,
        cap: cv2.VideoCapture,
        frame_count: int,
    ) -> list[ImageDocument]:
        """Extract key frames from video.

        Args:
            cap: OpenCV video capture object
            frame_count: Total number of frames

        Returns:
            List of ImageDocuments representing key frames
        """
        frames: list[ImageDocument] = []

        if frame_count == 0 or self.num_frames == 0:
            return frames

        # Calculate frame indices to extract (evenly distributed)
        interval = max(1, frame_count // self.num_frames)
        frame_indices = [i * interval for i in range(self.num_frames)]

        for idx in frame_indices:
            # Seek to frame and read (Blocking I/O)
            def _read_frame() -> Any:
                cap.set(cv2.CAP_PROP_POS_FRAMES, idx)
                return cap.read()

            ret, frame = await asyncio.to_thread(_read_frame)

            if not ret:
                continue

            # Heavy CPU processing in thread
            def _process_frame() -> Any:
                # Convert BGR to RGB
                _frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

                from PIL import Image

                _pil_image = Image.fromarray(_frame_rgb)

                # Resize if needed
                if self.frame_resize:
                    # Compatibility shim: PIL 10 uses Image.Resampling; older versions use Image.LANCZOS
                    resampling = getattr(Image, "Resampling", Image)
                    resample_filter = getattr(
                        resampling,
                        "LANCZOS",
                        getattr(Image, "LANCZOS", None),
                    )

                    if resample_filter is not None:
                        _pil_image.thumbnail(
                            (self.frame_resize, self.frame_resize),
                            resample_filter,
                        )
                    else:
                        _pil_image.thumbnail((self.frame_resize, self.frame_resize))

                # Convert to bytes
                import io

                _img_byte_arr = io.BytesIO()
                _pil_image.save(_img_byte_arr, format="JPEG")
                return _img_byte_arr.getvalue()

            img_bytes = await asyncio.to_thread(_process_frame)

            # Create ImageDocument (async call)
            frame_doc = await self.image_loader.load(
                img_bytes,
                caption=f"Frame {idx}",
            )
            frames.append(frame_doc)

        return frames

    async def _extract_audio(self, video_path: Path) -> AudioDocument | None:
        """Extract audio track from video.

        This uses ffmpeg to extract the audio track to a temporary file,
        then loads it with the AudioLoader.

        Args:
            video_path: Path to video file

        Returns:
            AudioDocument or None if no audio track
        """
        import subprocess
        import tempfile

        # Create temporary audio file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_audio:
            temp_audio_path = Path(temp_audio.name)

        try:
            # Extract audio with ffmpeg
            cmd = [
                "ffmpeg",
                "-i",
                str(video_path),
                "-vn",  # No video
                "-acodec",
                "pcm_s16le",  # PCM 16-bit little-endian
                "-ar",
                "16000",  # 16kHz sample rate
                "-ac",
                "1",  # Mono
                "-y",  # Overwrite output
                str(temp_audio_path),
            ]

            # cmd is constructed from fixed ffmpeg args and a validated file path (no shell=True)
            # Run in thread executor as it is blocking
            result = await asyncio.to_thread(
                subprocess.run,
                cmd,
                check=False,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60,
            )

            if result.returncode != 0:
                return None

            # Load audio with AudioLoader
            audio_doc = await self.audio_loader.load(temp_audio_path)
        except (subprocess.TimeoutExpired, FileNotFoundError, OSError):
            return None
        else:
            return audio_doc
        finally:
            # Clean up temp file
            if temp_audio_path.exists():
                temp_audio_path.unlink()

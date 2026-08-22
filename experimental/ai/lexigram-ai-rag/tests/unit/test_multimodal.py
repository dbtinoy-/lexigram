from __future__ import annotations

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from lexigram.ai.rag.multimodal import (
    AudioDocument,
    AudioFormat,
    ImageDocument,
    ImageFormat,
    ImageLoader,
    ImageMetadata,
    Modality,
    MultiModalDocument,
    MultiModalEmbedding,
    VideoDocument,
    VideoFormat,
)


class TestImageDocument:
    """Tests for ImageDocument."""

    def test_create_from_path(self):
        """Test creating ImageDocument from file path."""
        # Create temp file for testing
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            temp_path = Path(f.name)
            f.write(b"fake image")

        try:
            doc = ImageDocument(
                content=str(temp_path),
                format=ImageFormat.JPEG,
                width=1920,
                height=1080,
            )
            assert doc.content == str(temp_path)
            assert doc.format == ImageFormat.JPEG
            assert doc.width == 1920
            assert doc.height == 1080
        finally:
            temp_path.unlink()

    def test_create_from_bytes(self):
        """Test creating ImageDocument from bytes."""
        doc = ImageDocument(
            content=b"fake image bytes",
            format=ImageFormat.PNG,
            width=800,
            height=600,
        )
        assert isinstance(doc.content, bytes)
        assert doc.format == ImageFormat.PNG

    def test_aspect_ratio(self):
        """Test aspect ratio calculation."""
        doc = ImageDocument(
            content=b"bytes",
            format=ImageFormat.JPEG,
            width=1920,
            height=1080,
        )
        assert doc.aspect_ratio == pytest.approx(1.777, rel=0.01)

    def test_has_text(self):
        """Test has_text property."""
        doc = ImageDocument(
            content=b"bytes",
            format=ImageFormat.JPEG,
            width=100,
            height=100,
            text_content="Some OCR text",
        )
        assert doc.has_text is True

        doc.text_content = None
        assert doc.has_text is False

    def test_has_embedding(self):
        """Test has_embedding property."""
        doc = ImageDocument(
            content=b"bytes",
            format=ImageFormat.JPEG,
            width=100,
            height=100,
            embedding=[0.1, 0.2, 0.3],
        )
        assert doc.has_embedding is True

        doc.embedding = None
        assert doc.has_embedding is False

    def test_metadata(self):
        """Test ImageMetadata."""
        metadata = ImageMetadata(
            caption="Sunset over mountains",
            tags=["landscape", "sunset"],
            source="https://example.com/image.jpg",
        )
        doc = ImageDocument(
            content=b"bytes",
            format=ImageFormat.JPEG,
            width=100,
            height=100,
            metadata=metadata,
        )
        assert doc.metadata.caption == "Sunset over mountains"
        assert "landscape" in doc.metadata.tags


class TestAudioDocument:
    """Tests for AudioDocument."""

    def test_create_audio_document(self):
        """Test creating AudioDocument."""
        # Create temp file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            temp_path = Path(f.name)
            f.write(b"fake audio")

        try:
            doc = AudioDocument(
                content=str(temp_path),
                format=AudioFormat.MP3,
                duration=180.5,
                sample_rate=44100,
                channels=2,
            )
            assert doc.duration == 180.5
            assert doc.sample_rate == 44100
            assert doc.channels == 2
        finally:
            temp_path.unlink()

    def test_is_mono(self):
        """Test is_mono property."""
        doc = AudioDocument(
            content=b"bytes",
            format=AudioFormat.WAV,
            duration=10.0,
            sample_rate=16000,
            channels=1,
        )
        assert doc.is_mono is True
        assert doc.is_stereo is False

    def test_is_stereo(self):
        """Test is_stereo property."""
        doc = AudioDocument(
            content=b"bytes",
            format=AudioFormat.WAV,
            duration=10.0,
            sample_rate=16000,
            channels=2,
        )
        assert doc.is_stereo is True
        assert doc.is_mono is False

    def test_has_transcript(self):
        """Test has_transcript property."""
        doc = AudioDocument(
            content=b"bytes",
            format=AudioFormat.MP3,
            duration=10.0,
            sample_rate=16000,
            transcript="Hello world",
        )
        assert doc.has_transcript is True


class TestVideoDocument:
    """Tests for VideoDocument."""

    def test_create_video_document(self):
        """Test creating VideoDocument."""
        # Create temp file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            temp_path = Path(f.name)
            f.write(b"fake video")

        try:
            doc = VideoDocument(
                content=str(temp_path),
                format=VideoFormat.MP4,
                duration=300.0,
                fps=30.0,
                width=1920,
                height=1080,
            )
            assert doc.duration == 300.0
            assert doc.fps == 30.0
            assert doc.width == 1920
        finally:
            temp_path.unlink()

    def test_total_frames(self):
        """Test total_frames calculation."""
        doc = VideoDocument(
            content=b"bytes",
            format=VideoFormat.MP4,
            duration=10.0,
            fps=30.0,
            width=1920,
            height=1080,
        )
        assert doc.total_frames == 300

    def test_aspect_ratio(self):
        """Test aspect ratio calculation."""
        doc = VideoDocument(
            content=b"bytes",
            format=VideoFormat.MP4,
            duration=10.0,
            fps=30.0,
            width=1920,
            height=1080,
        )
        assert doc.aspect_ratio == pytest.approx(1.777, rel=0.01)

    def test_has_audio(self):
        """Test has_audio property."""
        audio = AudioDocument(
            content=b"bytes",
            format=AudioFormat.MP3,
            duration=10.0,
            sample_rate=16000,
        )
        doc = VideoDocument(
            content=b"bytes",
            format=VideoFormat.MP4,
            duration=10.0,
            fps=30.0,
            width=1920,
            height=1080,
            audio_track=audio,
        )
        assert doc.has_audio is True


class TestMultiModalDocument:
    """Tests for MultiModalDocument."""

    def test_create_multimodal_document(self):
        """Test creating MultiModalDocument."""
        doc = MultiModalDocument(
            text_content="Product review",
            metadata={"source": "blog", "category": "review"},
        )
        assert doc.text_content == "Product review"
        assert doc.metadata["source"] == "blog"

    def test_modalities(self):
        """Test modalities property."""
        image = ImageDocument(
            content=b"bytes",
            format=ImageFormat.JPEG,
            width=100,
            height=100,
        )
        doc = MultiModalDocument(
            text_content="Review",
            images=[image],
        )
        modalities = doc.modalities
        assert Modality.TEXT in modalities
        assert Modality.IMAGE in modalities
        assert Modality.AUDIO not in modalities

    def test_is_multimodal(self):
        """Test is_multimodal property."""
        doc = MultiModalDocument(text_content="Review")
        assert doc.is_multimodal is False

        image = ImageDocument(
            content=b"bytes",
            format=ImageFormat.JPEG,
            width=100,
            height=100,
        )
        doc.images.append(image)
        assert doc.is_multimodal is True

    def test_counts(self):
        """Test total counts."""
        doc = MultiModalDocument()
        assert doc.total_images == 0
        assert doc.total_audio == 0
        assert doc.total_videos == 0


class TestMultiModalEmbedding:
    """Tests for MultiModalEmbedding."""

    def test_available_modalities(self):
        """Test available_modalities property."""
        emb = MultiModalEmbedding(
            text=[0.1, 0.2],
            image=[0.3, 0.4],
            fusion_method="concat",
        )
        modalities = emb.available_modalities
        assert Modality.TEXT in modalities
        assert Modality.IMAGE in modalities
        assert Modality.AUDIO not in modalities

    def test_has_fused(self):
        """Test has_fused property."""
        emb = MultiModalEmbedding(
            text=[0.1, 0.2],
            fused=[0.1, 0.2, 0.3, 0.4],
        )
        assert emb.has_fused is True


# ============================================================================
# Test Loaders
# ============================================================================


class TestImageLoader:
    """Tests for ImageLoader."""

    @patch("lexigram.ai.rag.multimodal.loaders.image.PIL_AVAILABLE", True)
    @patch("lexigram.ai.rag.multimodal.loaders.image.Image")
    @pytest.mark.asyncio
    async def test_load_from_path(self, mock_image):
        """Test loading image from path."""
        # Mock PIL Image
        mock_img = Mock()
        mock_img.format = "JPEG"
        mock_img.width = 1920
        mock_img.height = 1080
        mock_img.mode = "RGB"
        mock_img.getexif.return_value = {}
        mock_image.open.return_value = mock_img

        loader = ImageLoader(extract_exif=False, extract_text=False)

        # Create a temporary file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            temp_path = Path(f.name)
            f.write(b"fake image")

        try:
            doc = await loader.load(temp_path)
            assert doc.format == ImageFormat.JPEG
            assert doc.width == 1920
            assert doc.height == 1080
        finally:
            temp_path.unlink()

    @patch("lexigram.ai.rag.multimodal.loaders.image.PIL_AVAILABLE", True)
    @patch("lexigram.ai.rag.multimodal.loaders.image.Image")
    @pytest.mark.asyncio
    async def test_load_from_bytes(self, mock_image):
        """Test loading image from bytes."""
        mock_img = Mock()
        mock_img.format = "PNG"
        mock_img.width = 800
        mock_img.height = 600
        mock_img.mode = "RGB"
        mock_img.getexif.return_value = {}
        mock_image.open.return_value = mock_img

        loader = ImageLoader()
        doc = await loader.load(b"fake image bytes")
        assert doc.format == ImageFormat.PNG

    @patch("lexigram.ai.rag.multimodal.loaders.image.PIL_AVAILABLE", False)
    def test_requires_pil(self, monkeypatch):
        """Test that PIL is required."""
        # Simulate ImportError when attempting to import PIL modules
        import builtins

        real_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "PIL" or name.startswith("PIL."):
                raise ImportError("No module named PIL")
            return real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        with pytest.raises(ImportError, match="PIL/Pillow is required"):
            ImageLoader()

    @patch("lexigram.ai.rag.multimodal.loaders.image.PIL_AVAILABLE", True)
    def test_requires_pytesseract_when_requested(self, monkeypatch):
        """If OCR is requested, pytesseract must be available."""
        # Simulate ImportError when attempting to import pytesseract
        import builtins

        real_import = builtins.__import__

        def fake_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "pytesseract" or name.startswith("pytesseract."):
                raise ImportError("No module named pytesseract")
            return real_import(name, globals, locals, fromlist, level)

        monkeypatch.setattr(builtins, "__import__", fake_import)

        with pytest.raises(ImportError, match="pytesseract is required"):
            ImageLoader(extract_text=True)

    @patch("lexigram.ai.rag.multimodal.loaders.image.PIL_AVAILABLE", True)
    def test_extract_text_with_mocked_pytesseract(self):
        """Test that _extract_text uses the global _pytesseract when available."""
        # Create loader without OCR import to avoid requiring real pytesseract
        loader = ImageLoader(extract_text=False)

        # Mock image and pytesseract
        mock_img = Mock()
        mock_img.mode = "RGB"
        # Patch the module-level _pytesseract and TESSERACT_AVAILABLE
        from lexigram.ai.rag.multimodal.loaders import image as image_mod

        image_mod._pytesseract = Mock()
        image_mod._pytesseract.image_to_string.return_value = "Detected text"
        image_mod.TESSERACT_AVAILABLE = True

        # Enable extraction and call internal method
        loader.extract_text = True
        text = loader._extract_text(mock_img)
        assert text == "Detected text"

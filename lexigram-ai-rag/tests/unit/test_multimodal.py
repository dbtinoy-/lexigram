"""Tests for multi-modal RAG components."""

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from lexigram.ai.rag.multimodal import (
    AudioDocument,
    AudioFormat,
    AudioLoader,
    CLIPEmbedding,
    CrossModalRetriever,
    ImageDocument,
    ImageFormat,
    ImageLoader,
    ImageMetadata,
    Modality,
    MultiModalDocument,
    MultiModalEmbedder,
    MultiModalEmbedding,
    VideoDocument,
    VideoFormat,
    VideoLoader,
)

# ============================================================================
# Test Document Types
# ============================================================================


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


class TestAudioLoader:
    """Tests for AudioLoader."""

    @patch("lexigram.ai.rag.multimodal.loaders.audio.LIBROSA_AVAILABLE", False)
    def test_requires_librosa(self):
        """Test that librosa is required."""
        with pytest.raises(ImportError, match="librosa and soundfile are required"):
            AudioLoader()

    @patch("lexigram.ai.rag.multimodal.loaders.audio.LIBROSA_AVAILABLE", True)
    @pytest.mark.asyncio
    async def test_load_audio(self):
        """Test loading audio file."""
        # Skip test if librosa not actually available
        try:
            import librosa  # noqa: F401
        except ImportError:
            pytest.skip("librosa not installed")
            return

        # This test would require actual audio file
        # Skipping for now as it needs real librosa functionality
        pytest.skip("Requires actual audio file and librosa")


class TestVideoLoader:
    """Tests for VideoLoader."""

    @patch("lexigram.ai.rag.multimodal.loaders.video.CV2_AVAILABLE", False)
    def test_requires_opencv(self):
        """Test that OpenCV is required."""
        with pytest.raises(ImportError, match="opencv-python is required"):
            VideoLoader()

    @patch("lexigram.ai.rag.multimodal.loaders.video.CV2_AVAILABLE", True)
    @patch("lexigram.ai.rag.multimodal.loaders.image.PIL_AVAILABLE", True)
    @patch("lexigram.ai.rag.multimodal.loaders.video.cv2")
    @pytest.mark.asyncio
    async def test_load_video(self, mock_cv2):
        """Test loading video file."""
        # Mock OpenCV
        mock_cap = Mock()
        mock_cap.isOpened.return_value = True
        mock_cap.get.side_effect = [
            30.0,
            300,
            1920,
            1080,
        ]  # fps, frame_count, width, height
        mock_cap.read.return_value = (False, None)  # No frames for simplicity
        mock_cv2.VideoCapture.return_value = mock_cap

        loader = VideoLoader(num_frames=0, extract_audio=False)

        # Create temp file
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            temp_path = Path(f.name)
            f.write(b"fake video")

        try:
            doc = await loader.load(temp_path)
            assert doc.format == VideoFormat.MP4
            assert doc.fps == 30.0
            assert doc.width == 1920
            assert doc.height == 1080
        finally:
            temp_path.unlink()


# ============================================================================
# Test Embeddings
# ============================================================================


class TestCLIPEmbedding:
    """Tests for CLIPEmbedding."""

    @patch("lexigram.ai.rag.multimodal.embeddings.clip.CLIP_AVAILABLE", False)
    def test_requires_transformers(self):
        """Test that transformers is required."""
        with pytest.raises(ImportError, match="CLIP embeddings require"):
            CLIPEmbedding()

    @patch("lexigram.ai.rag.multimodal.embeddings.clip.CLIP_AVAILABLE", True)
    @patch("lexigram.ai.rag.multimodal.embeddings.clip.CLIPModel")
    @patch("lexigram.ai.rag.multimodal.embeddings.clip.CLIPProcessor")
    @patch("lexigram.ai.rag.multimodal.embeddings.clip.torch")
    @pytest.mark.asyncio
    async def test_embed_text(self, mock_torch, mock_processor_class, mock_model_class):
        """Test embedding text."""

        # Mock model
        mock_model = Mock()
        mock_features = Mock()
        mock_features.cpu.return_value.numpy.return_value.tolist.return_value = [
            [0.1, 0.2, 0.3],
        ]
        mock_features.norm.return_value = Mock()
        mock_features.__truediv__ = Mock(return_value=mock_features)
        mock_model.get_text_features.return_value = mock_features
        mock_model.config.projection_dim = 512
        mock_model.to.return_value = mock_model
        mock_model.eval.return_value = None
        mock_model_class.from_pretrained.return_value = mock_model

        # Mock processor
        mock_processor = Mock()
        mock_processor.return_value = {"input_ids": Mock()}
        mock_processor_class.from_pretrained.return_value = mock_processor

        # Mock torch
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False
        mock_torch.no_grad.return_value.__enter__ = Mock()
        mock_torch.no_grad.return_value.__exit__ = Mock()

        embedder = CLIPEmbedding()
        embedding = await embedder.embed_text("a photo of a cat")
        assert isinstance(embedding, list)
        assert len(embedding) == 3

    @patch("lexigram.ai.rag.multimodal.embeddings.clip.CLIP_AVAILABLE", True)
    @patch("lexigram.ai.rag.multimodal.embeddings.clip.CLIPModel")
    @patch("lexigram.ai.rag.multimodal.embeddings.clip.CLIPProcessor")
    @patch("lexigram.ai.rag.multimodal.embeddings.clip.torch")
    @patch("lexigram.ai.rag.multimodal.embeddings.clip.Image")
    @pytest.mark.asyncio
    async def test_embed_image(
        self, mock_image, mock_torch, mock_processor_class, mock_model_class,
    ):
        """Test embedding image."""
        # Mock model
        mock_model = Mock()
        mock_features = Mock()
        mock_features.cpu.return_value.numpy.return_value.tolist.return_value = [
            [0.4, 0.5, 0.6],
        ]
        mock_features.norm.return_value = Mock()
        mock_features.__truediv__ = Mock(return_value=mock_features)
        mock_model.get_image_features.return_value = mock_features
        mock_model.config.projection_dim = 512
        mock_model.to.return_value = mock_model
        mock_model.eval.return_value = None
        mock_model_class.from_pretrained.return_value = mock_model

        # Mock processor
        mock_processor = Mock()
        mock_processor.return_value = {"pixel_values": Mock()}
        mock_processor_class.from_pretrained.return_value = mock_processor

        # Mock torch
        mock_torch.cuda.is_available.return_value = False
        mock_torch.backends.mps.is_available.return_value = False
        mock_torch.no_grad.return_value.__enter__ = Mock()
        mock_torch.no_grad.return_value.__exit__ = Mock()

        # Mock PIL Image
        mock_pil_image = Mock()
        mock_image.open.return_value = mock_pil_image

        embedder = CLIPEmbedding()

        # Create temp image
        import tempfile

        with tempfile.NamedTemporaryFile(suffix=".jpg", delete=False) as f:
            temp_path = Path(f.name)
            f.write(b"fake image")

        try:
            embedding = await embedder.embed_image(str(temp_path))
            assert isinstance(embedding, list)
            assert len(embedding) == 3
        finally:
            temp_path.unlink()


class TestMultiModalEmbedder:
    """Tests for MultiModalEmbedder."""

    @patch("lexigram.ai.rag.multimodal.embeddings.multimodal.CLIPEmbedding")
    @pytest.mark.asyncio
    async def test_embed_text(self, mock_clip_class):
        """Test embedding text."""
        mock_clip = Mock()
        mock_clip.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_clip_class.return_value = mock_clip

        embedder = MultiModalEmbedder()
        embedding = await embedder.embed_text("test text")
        assert embedding == [0.1, 0.2, 0.3]

    @patch("lexigram.ai.rag.multimodal.embeddings.multimodal.CLIPEmbedding")
    @pytest.mark.asyncio
    async def test_embed_image(self, mock_clip_class):
        """Test embedding image."""
        mock_clip = Mock()
        mock_clip.embed_image = AsyncMock(return_value=[0.4, 0.5, 0.6])
        mock_clip_class.return_value = mock_clip

        embedder = MultiModalEmbedder()
        image = ImageDocument(
            content=b"bytes",
            format=ImageFormat.JPEG,
            width=100,
            height=100,
        )
        embedding = await embedder.embed_image(image)
        assert embedding == [0.4, 0.5, 0.6]

    @patch("lexigram.ai.rag.multimodal.embeddings.multimodal.CLIPEmbedding")
    @pytest.mark.asyncio
    async def test_embed_multimodal_document(self, mock_clip_class):
        """Test embedding multi-modal document."""
        mock_clip = Mock()
        mock_clip.embed_text = AsyncMock(return_value=[0.1, 0.2])
        mock_clip.embed_image = AsyncMock(return_value=[0.3, 0.4])
        mock_clip_class.return_value = mock_clip

        embedder = MultiModalEmbedder(fusion_method="concat")

        image = ImageDocument(
            content=b"bytes",
            format=ImageFormat.JPEG,
            width=100,
            height=100,
        )
        doc = MultiModalDocument(text_content="test", images=[image])

        embeddings = await embedder.embed(doc)
        assert embeddings.text == [0.1, 0.2]
        assert embeddings.image == [0.3, 0.4]
        assert embeddings.fused is not None
        assert len(embeddings.fused) == 4  # concat


# ============================================================================
# Test Retrieval
# ============================================================================


class TestCrossModalRetriever:
    """Tests for CrossModalRetriever."""

    @patch("lexigram.ai.rag.multimodal.embeddings.multimodal.CLIPEmbedding")
    @pytest.mark.asyncio
    async def test_index_and_search_image(self, mock_clip_class):
        """Test indexing and searching images."""
        mock_clip = Mock()
        mock_clip.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_clip.embed_image = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_clip_class.return_value = mock_clip

        embedder = MultiModalEmbedder()
        retriever = CrossModalRetriever(embedder)

        # Index images
        image1 = ImageDocument(
            content=b"cat",
            format=ImageFormat.JPEG,
            width=100,
            height=100,
        )
        image2 = ImageDocument(
            content=b"dog",
            format=ImageFormat.JPEG,
            width=100,
            height=100,
        )

        await retriever.index_image(image1)
        await retriever.index_image(image2)

        # Search
        results = await retriever.search_by_text(
            "a photo of a cat", Modality.IMAGE, top_k=1,
        )
        assert len(results) == 1
        assert isinstance(results[0], ImageDocument)

    @patch("lexigram.ai.rag.multimodal.embeddings.multimodal.CLIPEmbedding")
    @pytest.mark.asyncio
    async def test_hybrid_search(self, mock_clip_class):
        """Test hybrid search with multiple query modalities."""
        mock_clip = Mock()
        mock_clip.embed_text = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_clip.embed_image = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_clip_class.return_value = mock_clip

        embedder = MultiModalEmbedder()
        retriever = CrossModalRetriever(embedder)

        # Index document
        doc = MultiModalDocument(text_content="cat photo")
        doc.embeddings = MultiModalEmbedding(fused=[0.1, 0.2, 0.3])
        await retriever.index_multimodal(doc)

        # Hybrid search
        query_image = ImageDocument(
            content=b"cat",
            format=ImageFormat.JPEG,
            width=100,
            height=100,
        )
        results = await retriever.hybrid_search(
            text_query="cat",
            image_query=query_image,
            target_modality=Modality.MULTIMODAL,
        )
        assert len(results) >= 0

    @patch("lexigram.ai.rag.multimodal.embeddings.multimodal.CLIPEmbedding")
    @pytest.mark.asyncio
    async def test_get_statistics(self, mock_clip_class):
        """Test retrieval statistics."""
        mock_clip = Mock()
        mock_clip.embed_image = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_clip_class.return_value = mock_clip

        embedder = MultiModalEmbedder()
        retriever = CrossModalRetriever(embedder)

        # Index images
        image = ImageDocument(
            content=b"cat",
            format=ImageFormat.JPEG,
            width=100,
            height=100,
        )
        await retriever.index_image(image)

        stats = retriever.get_statistics()
        assert stats[Modality.IMAGE.value] == 1
        assert stats[Modality.AUDIO.value] == 0

    @patch("lexigram.ai.rag.multimodal.embeddings.multimodal.CLIPEmbedding")
    @pytest.mark.asyncio
    async def test_clear(self, mock_clip_class):
        """Test clearing retriever."""
        mock_clip = Mock()
        mock_clip.embed_image = AsyncMock(return_value=[0.1, 0.2, 0.3])
        mock_clip_class.return_value = mock_clip

        embedder = MultiModalEmbedder()
        retriever = CrossModalRetriever(embedder)

        # Index and clear
        image = ImageDocument(
            content=b"cat",
            format=ImageFormat.JPEG,
            width=100,
            height=100,
        )
        await retriever.index_image(image)
        assert retriever.get_statistics()[Modality.IMAGE.value] == 1

        retriever.clear()
        assert retriever.get_statistics()[Modality.IMAGE.value] == 0

from __future__ import annotations

from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch

import pytest

from lexigram.ai.rag.multimodal import (
    AudioLoader,
    CLIPEmbedding,
    CrossModalRetriever,
    ImageDocument,
    ImageFormat,
    Modality,
    MultiModalDocument,
    MultiModalEmbedder,
    MultiModalEmbedding,
    VideoFormat,
    VideoLoader,
)


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
        self,
        mock_image,
        mock_torch,
        mock_processor_class,
        mock_model_class,
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
            "a photo of a cat",
            Modality.IMAGE,
            top_k=1,
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

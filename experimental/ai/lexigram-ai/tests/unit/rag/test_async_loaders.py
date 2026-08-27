
import pytest
pytest.importorskip("lexigram.ai.rag", reason="lexigram-ai-rag not installed")

import asyncio
import importlib.util
from pathlib import Path
from unittest.mock import AsyncMock, Mock, patch, mock_open


from lexigram.ai.rag.loaders.core import PDFLoader
from lexigram.ai.rag.multimodal.loaders.image import ImageLoader
from lexigram.ai.rag.multimodal.loaders.video import VideoLoader, VideoLoaderError
from lexigram.ai.llm.pricing.sources import JSONFilePricingSource

_cv2_available = importlib.util.find_spec("cv2") is not None

class TestAsyncLoaders:
    
    @pytest.mark.asyncio
    async def test_pdf_loader_async_exists(self):
        """Verify PDFLoader uses asyncio.to_thread for exists check."""
        loader = PDFLoader()
        path_str = "test.pdf"
        
        # We need to mock Path.exists. Since PDFLoader creates a new Path(source),
        # matching the exact instance calls is tricky. 
        # But we can patch asyncio.to_thread and see if it's called with the bound method.
        
        # Patch pypdf so import succeeds
        with patch.dict("sys.modules", {"pypdf": Mock()}):
            with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
                mock_to_thread.return_value = False # Simulate file not found
                
                # This triggers the exists check
                try:
                    await loader.load(path_str)
                except Exception:
                    pass
                
                # Verify to_thread was called.
                assert mock_to_thread.called

    @pytest.mark.asyncio
    async def test_pricing_source_async_io(self):
        """Verify JSONFilePricingSource uses asyncio.to_thread for file ops."""
        # Use a path that we can mock easily
        path = Path("prices.json")
        source = JSONFilePricingSource(path)
        
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            # First call is exists, return True. Second call is read, return "{}"
            mock_to_thread.side_effect = [True, b'{"models": {}}']
            
            await source._load_cache()
            
            assert mock_to_thread.call_count >= 1

    @pytest.mark.asyncio
    async def test_image_loader_parallel_batch(self):
        """Verify ImageLoader.load_batch runs concurrently."""
        import lexigram.ai.rag.multimodal.loaders.image as image_mod

        with patch.object(image_mod, "PIL_AVAILABLE", True):
            loader = ImageLoader()
        # Mock load to avoid actual I/O
        loader.load = AsyncMock(return_value=Mock(spec=str)) 
        
        # Mock gather to await tasks to avoid RuntimeWarning
        async def mock_gather_side_effect(*tasks, **kwargs):
            for t in tasks:
                await t
            return []

        with patch("asyncio.gather", new_callable=AsyncMock) as mock_gather:
            mock_gather.side_effect = mock_gather_side_effect
            
            sources = ["img1.jpg", "img2.jpg"]
            await loader.load_batch(sources)
            
            assert mock_gather.called
            assert len(mock_gather.call_args[0]) == 2

    @pytest.mark.skipif(not _cv2_available, reason="opencv-python not installed")
    @pytest.mark.asyncio
    async def test_video_loader_fixed_name_errors(self):
        """Verify VideoLoader handles errors correctly (no NameErrors)."""
        # extract_audio=False prevents AudioLoader init (and librosa requirement)
        loader = VideoLoader(extract_audio=False)
        
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = False # exists = False
            
            with pytest.raises(VideoLoaderError) as exc:
                await loader.load("missing.mp4")
            
            assert "Video file not found" in str(exc.value)

    @pytest.mark.skipif(not _cv2_available, reason="opencv-python not installed")
    @pytest.mark.asyncio
    async def test_video_loader_unsupported_format(self):
        """Verify VideoLoader handles unsupported formats."""
        loader = VideoLoader(extract_audio=False)
        
        with patch("asyncio.to_thread", new_callable=AsyncMock) as mock_to_thread:
            mock_to_thread.return_value = True # exists = True
            
            with pytest.raises(VideoLoaderError) as exc:
                await loader.load("video.unknown")
                
            assert "Unsupported video format" in str(exc.value)

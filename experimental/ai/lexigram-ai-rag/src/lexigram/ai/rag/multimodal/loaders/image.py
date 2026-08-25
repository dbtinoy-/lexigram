"""Image loader for multi-modal RAG.

This module provides loading capabilities for image documents with support for:
- Multiple formats: JPEG, PNG, GIF, WebP, BMP, TIFF, SVG
- EXIF metadata extraction
- Optional OCR text extraction
- Image validation and normalization
"""

from __future__ import annotations

import asyncio
import io
from pathlib import Path
import sys
from typing import TYPE_CHECKING, Any, cast

from lexigram.logging import (
    get_logger,
)

if TYPE_CHECKING:
    from collections.abc import Mapping

logger = get_logger(__name__)

# Defer heavy imports (Pillow, pytesseract) until runtime to avoid import-time failures
# The loader will attempt to import these when needed and raise helpful errors if missing.
Image: Any = None
TAGS: Mapping[int, str] = {}
PIL_AVAILABLE = False

_pytesseract = None
TESSERACT_AVAILABLE = False

if TYPE_CHECKING:
    # Use `from PIL.Image import Image` so we reference the PIL Image *class* for typing
    from PIL.Image import Image as PILImage

    PILImageType = PILImage
else:
    PILImageType: Any = Any

# Make a small runtime alias for the PIL Image type to aid type inference
# (the actual Image object is assigned at runtime when Pillow is available)
PILImageTypeRuntime: Any = PILImageType

from lexigram.ai.rag.exceptions import ImageLoaderError
from lexigram.ai.rag.multimodal.types import (
    ImageDocument,
    ImageFormat,
    ImageMetadata,
)


def __getattr__(name: str) -> Any:
    """Allow module-level attribute assignments for lazy optional imports.

    This satisfies mypy while still allowing runtime lazy loading of Pillow
    and pytesseract.  The actual attributes (Image, TAGS, PIL_AVAILABLE,
    _pytesseract, TESSERACT_AVAILABLE) are set at runtime in __init__.
    """
    if name in {
        "Image",
        "TAGS",
        "PIL_AVAILABLE",
        "_pytesseract",
        "TESSERACT_AVAILABLE",
    }:
        try:
            return sys.modules[__name__].__dict__[name]
        except KeyError:
            pass
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


class ImageLoader:
    """Loader for image documents.

    Supports loading images from files or bytes with optional:
    - EXIF metadata extraction
    - OCR text extraction
    - Format validation
    - Image normalization

    Args:
        extract_exif: Whether to extract EXIF metadata
        extract_text: Whether to perform OCR text extraction
        tesseract_config: Custom tesseract configuration string
        max_size: Maximum image dimension (resize if larger)
        convert_to_rgb: Convert images to RGB mode

    Example:
        >>> loader = ImageLoader(extract_text=True)
        >>> doc = await loader.load("/path/to/image.jpg")
        >>> print(doc.text_content)
        "Extracted text from image"
    """

    def __init__(
        self,
        extract_exif: bool = True,
        extract_text: bool = False,
        tesseract_config: str = "--psm 3",
        max_size: int | None = None,
        convert_to_rgb: bool = False,
    ):
        """Initialize image loader."""
        # Try to import Pillow lazily (so importing this module doesn't require Pillow)
        mod = sys.modules[__name__]
        # If tests have patched PIL_AVAILABLE, respect that and avoid re-importing
        # Use getattr on the actual module object to read the live value (which
        # may have been patched at runtime) rather than the module-level constant
        # captured at import time.
        _pil_available = getattr(mod, "PIL_AVAILABLE", False)
        if not _pil_available:
            try:
                from PIL import Image as _Image
                from PIL.ExifTags import TAGS as _TAGS

                mod.Image = _Image  # type: ignore[attr-defined]
                mod.TAGS = _TAGS  # type: ignore[attr-defined]
                mod.PIL_AVAILABLE = True  # type: ignore[attr-defined]
            except (ImportError, ModuleNotFoundError):
                mod.PIL_AVAILABLE = False  # type: ignore[attr-defined]

        _current_pil = getattr(mod, "PIL_AVAILABLE", False)
        if not _current_pil:
            raise ImportError(
                "PIL/Pillow is required for image loading. Install with: pip install Pillow",
            )

        # Lazy import of pytesseract only if OCR is requested
        if extract_text:
            try:
                import pytesseract as _pt

                mod._pytesseract = _pt  # type: ignore[attr-defined]
                mod.TESSERACT_AVAILABLE = True  # type: ignore[attr-defined]
            except (ImportError, ModuleNotFoundError):
                mod.TESSERACT_AVAILABLE = False  # type: ignore[attr-defined]

        _tesseract_available = getattr(mod, "TESSERACT_AVAILABLE", False)
        if extract_text and not _tesseract_available:
            raise ImportError(
                "pytesseract is required for OCR. Install with: pip install pytesseract",
            )

        self.extract_exif = extract_exif
        self.extract_text = extract_text

        # Validate tesseract_config to prevent command injection
        # Only allow alphanumeric, spaces, and specific flags
        import re

        if not re.match(r"^[a-zA-Z0-9\s\-\.\_=]*$", tesseract_config):
            msg = f"Insecure tesseract_config detected: {tesseract_config}"
            raise ValueError(msg)

        self.tesseract_config = tesseract_config
        self.max_size = max_size
        self.convert_to_rgb = convert_to_rgb

    async def load(
        self,
        source: str | Path | bytes,
        caption: str | None = None,
        alt_text: str | None = None,
        source_url: str | None = None,
        **metadata_kwargs: Any,
    ) -> ImageDocument:
        """Load an image document.

        Args:
            source: File path, URL, or raw bytes
            caption: Optional image caption
            alt_text: Optional alt text
            source_url: Optional source URL
            **metadata_kwargs: Additional metadata fields

        Returns:
            ImageDocument with loaded image data

        Raises:
            ImageLoaderError: If loading fails
        """
        try:
            # Load image
            content: bytes | str
            file_path: Path | None

            if isinstance(source, (str, Path)):
                file_path = Path(source)
                if not await asyncio.to_thread(file_path.exists):
                    msg = f"Image file not found: {source}"
                    raise ImageLoaderError(msg)

                # Image.open is lazy, but it still performs initial I/O
                img = await asyncio.to_thread(Image.open, file_path)
                pil_img = cast("PILImageType", img)
                content = str(file_path)
            elif isinstance(source, bytes):
                # BytesIO is memory-only, but Image.open still does format detection/header parsing
                img = await asyncio.to_thread(Image.open, io.BytesIO(source))
                pil_img = cast("PILImageType", img)
                content = source
                file_path = None
            else:
                msg = f"Unsupported source type: {type(source)}"
                raise ImageLoaderError(msg)

            # Detect format (fast)
            image_format = self._detect_format(pil_img)

            # Convert mode if requested (CPU intensive)
            if self.convert_to_rgb and pil_img.mode != "RGB":
                pil_img = await asyncio.to_thread(pil_img.convert, "RGB")

            # Resize if needed (CPU intensive)
            if self.max_size:
                pil_img = await asyncio.to_thread(
                    self._resize_image,
                    pil_img,
                    self.max_size,
                )

            # Extract EXIF metadata (fast/I/O already done)
            exif_data = {}
            if self.extract_exif:
                exif_data = await asyncio.to_thread(self._extract_exif, pil_img)

            # Build metadata
            metadata = ImageMetadata(
                caption=caption,
                alt_text=alt_text,
                source=source_url,
                exif=exif_data,
                **metadata_kwargs,
            )

            # Extract text via OCR (Extremely CPU intensive)
            text_content = None
            if self.extract_text:
                text_content = await asyncio.to_thread(self._extract_text, img)

            # Create document
            return ImageDocument(
                content=content,
                format=image_format,
                width=pil_img.width,
                height=pil_img.height,
                metadata=metadata,
                text_content=text_content,
                file_path=file_path,
            )

        except Exception as e:
            if isinstance(e, ImageLoaderError):
                raise
            msg = f"Failed to load image {source!r}: {e}"
            raise ImageLoaderError(msg) from e

    async def load_batch(
        self,
        sources: list[str | Path | bytes],
        **kwargs: Any,
    ) -> list[ImageDocument]:
        """Load multiple images.

        Args:
            sources: List of image sources
            **kwargs: Common metadata for all images

        Returns:
            List of loaded ImageDocuments
        """
        if not sources:
            return []

        async def _safe_load(source) -> Any:
            try:
                return await self.load(source, **kwargs)
            except ImageLoaderError as e:
                logger.warning("Failed to load image %r: %s", source, e)
                return None

        tasks = [_safe_load(source) for source in sources]
        results = await asyncio.gather(*tasks)
        return [doc for doc in results if doc is not None]

    def _detect_format(self, img: PILImage) -> ImageFormat:
        """Detect image format.

        Args:
            img: PIL Image object

        Returns:
            ImageFormat enum value
        """
        format_str = img.format
        if not format_str:
            msg = "Unable to detect image format"
            raise ImageLoaderError(msg)

        format_str = format_str.lower()

        # Map PIL format to our enum
        format_mapping = {
            "jpeg": ImageFormat.JPEG,
            "jpg": ImageFormat.JPG,
            "png": ImageFormat.PNG,
            "gif": ImageFormat.GIF,
            "webp": ImageFormat.WEBP,
            "bmp": ImageFormat.BMP,
            "tiff": ImageFormat.TIFF,
            "svg": ImageFormat.SVG,
        }

        if format_str not in format_mapping:
            msg = f"Unsupported image format: {format_str}"
            raise ImageLoaderError(msg)

        return format_mapping[format_str]

    def _extract_exif(self, img: PILImage) -> dict[str, Any]:
        """Extract EXIF metadata from image.

        Args:
            img: PIL Image object

        Returns:
            Dictionary of EXIF data
        """
        exif_data = {}

        try:
            exif = img.getexif()
            if exif:
                for tag_id, raw_value in exif.items():
                    tag = str(TAGS.get(tag_id, tag_id))
                    # Convert bytes to string for JSON serialization
                    value: str | bytes = raw_value
                    if isinstance(raw_value, bytes):
                        try:
                            value = raw_value.decode("utf-8")
                        except UnicodeDecodeError:
                            value = str(raw_value)
                    exif_data[tag] = value
        except (ValueError, TypeError, RuntimeError) as e:
            # EXIF extraction is optional, don't fail
            logger.warning("Failed to extract EXIF data: %s", e)

        return exif_data

    def _extract_text(self, img: PILImage) -> str:
        """Extract text from image using OCR.

        Args:
            img: PIL Image object

        Returns:
            Extracted text
        """
        if not self.extract_text:
            return ""

        if not TESSERACT_AVAILABLE or _pytesseract is None:
            msg = "Tesseract OCR not available or not installed"
            raise ImportError(msg)

        try:
            text = _pytesseract.image_to_string(img, config=self.tesseract_config)
            return text.strip()
        except (ValueError, TypeError, RuntimeError, OSError) as e:
            logger.warning("OCR extraction failed: %s", e)
            return ""

    def _resize_image(self, img: PILImage, max_size: int) -> PILImage:
        """Resize image if larger than max_size.

        Args:
            img: PIL Image object
            max_size: Maximum dimension

        Returns:
            Resized image (or original if already small enough)
        """
        if max(img.width, img.height) <= max_size:
            return img

        # Calculate new dimensions maintaining aspect ratio
        if img.width > img.height:
            new_width = max_size
            new_height = int(img.height * (max_size / img.width))
        else:
            new_height = max_size
            new_width = int(img.width * (max_size / img.height))

        return img.resize((new_width, new_height), Image.Resampling.LANCZOS)

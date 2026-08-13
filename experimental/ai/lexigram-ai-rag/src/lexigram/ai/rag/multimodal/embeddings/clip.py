"""CLIP embeddings for cross-modal image-text retrieval.

This module provides CLIP (Contrastive Language-Image Pre-training) embeddings
that create aligned vector spaces for images and text, enabling:
- Text-to-image search
- Image-to-text search
- Image similarity search
- Zero-shot image classification
"""

from __future__ import annotations

from pathlib import Path
import sys
from typing import TYPE_CHECKING, Any, cast

if TYPE_CHECKING:
    from PIL.Image import Image as PILImage

    PILImageType = PILImage
else:
    PILImageType: Any = Any

# Runtime optional dependency enforcement: imports happen lazily inside the
# CLIPEmbedding constructor to avoid import-time failures in environments
# where heavy ML packages are not installed. Use helper to give actionable
# error messages when required packages are missing.

from lexigram.ai.rag.deps import MissingOptionalDependencyError, ensure_packages


def __getattr__(name: str) -> Any:
    """Allow module-level attribute assignments for lazy optional imports.

    This satisfies mypy while still allowing runtime lazy loading of CLIP
    dependencies.  The actual attributes (CLIPModel, CLIPProcessor, torch,
    Image) are set at runtime in the constructor.
    """
    if name in {"CLIPModel", "CLIPProcessor", "torch", "Image"}:
        try:
            return sys.modules[__name__].__dict__[name]
        except KeyError:
            pass
    msg = f"module {__name__!r} has no attribute {name!r}"
    raise AttributeError(msg)


# Module-level placeholders populated at runtime when the packages are available
torch: Any = None
Image: Any = None
CLIPModel: Any | None = None
CLIPProcessor: Any | None = None

# Backwards-compat shim for existing tests that patch this variable
CLIP_AVAILABLE = False

from lexigram.ai.rag.exceptions import CLIPEmbeddingError
from lexigram.ai.rag.multimodal.types import ImageDocument


class CLIPEmbedding:
    """CLIP embeddings for images and text.

    Uses OpenAI's CLIP model to create aligned embeddings for images and text
    in the same vector space, enabling cross-modal retrieval.

    Args:
        model_name: CLIP model name from HuggingFace
        device: Device to run model on ("cpu", "cuda", "mps")
        batch_size: Batch size for processing multiple items

    Example:
        >>> embedder = CLIPEmbedding()
        >>> # Embed text
        >>> text_emb = await embedder.embed_text("a photo of a cat")
        >>> # Embed image
        >>> img_emb = await embedder.embed_image(image_doc)
        >>> # Compute similarity
        >>> similarity = cosine_similarity(text_emb, img_emb)
    """

    def __init__(
        self,
        model_name: str = "openai/clip-vit-base-patch32",
        device: str | None = None,
        batch_size: int = 32,
    ):
        """Initialize CLIP embedder."""
        # If test suite or older callers set CLIP_AVAILABLE to True, honor that
        # and avoid importing the heavy runtime packages (they will be patched
        # in tests). Otherwise, ensure the optional packages are present and
        # perform lazy imports.
        mod = sys.modules[__name__]
        if not CLIP_AVAILABLE:
            try:
                _ = ensure_packages(
                    ["transformers", "torch", "PIL"],
                    hint="pip install 'lexigram-ai[llm]' or 'lexigram-ai[all]'",
                )
            except MissingOptionalDependencyError as e:
                msg = (
                    "CLIP embeddings require transformers, torch, and pillow. "
                    "Install with: pip install 'lexigram-ai[llm]' or 'lexigram-ai[all]'."
                )
                raise ImportError(msg) from e

            # Perform actual imports now that availability is asserted.
            # Wrap imports and re-raise a consistent ImportError so tests and
            # callers see a helpful message rather than package internals.
            try:
                from PIL import Image as _Image
                import torch as _torch
                from transformers import (
                    CLIPModel as _CLIPModel,
                )
                from transformers import CLIPProcessor as _CLIPProcessor
            except Exception as e:
                msg = (
                    "CLIP embeddings require transformers, torch, and pillow. "
                    "Install with: pip install 'lexigram-ai[llm]' or 'lexigram-ai[all]'."
                )
                raise ImportError(msg) from e

            mod.CLIPModel = _CLIPModel  # type: ignore[attr-defined]
            mod.CLIPProcessor = _CLIPProcessor  # type: ignore[attr-defined]
            # Also update the local module-level bindings so that subsequent
            # references (e.g. `torch.cuda`) work correctly within this process.
            torch = _torch
            Image = _Image
        else:
            # CLIP_AVAILABLE True -> assume tests or caller patched module-level
            # symbols (CLIPModel/CLIPProcessor/torch/Image). If one is missing,
            # let normal attribute access/patching handle the failure in tests.
            torch = sys.modules.get("lexigram.ai.rag.multimodal.embeddings.clip").torch  # type: ignore[union-attr]

        self.model_name = model_name
        self.batch_size = batch_size

        # Auto-detect device
        if device is None:
            cuda_mod = getattr(torch, "cuda", None)
            mps_mod = getattr(getattr(torch, "backends", None), "mps", None)
            if cuda_mod and getattr(cuda_mod, "is_available", lambda: False)():
                device = "cuda"
            elif mps_mod and getattr(mps_mod, "is_available", lambda: False)():
                device = "mps"
            else:
                device = "cpu"
        self.device = device

        # Load model and processor
        self._model: Any | None = None
        self._processor: Any | None = None
        self._load_model()

    def _load_model(self) -> Any:
        """Load CLIP model and processor."""
        try:
            self._processor = CLIPProcessor.from_pretrained(self.model_name)  # type: ignore[union-attr]
            self._model = CLIPModel.from_pretrained(self.model_name)  # type: ignore[union-attr]
            self._model.to(self.device)
            self._model.eval()
        except Exception as e:
            msg = f"Failed to load CLIP model: {e}"
            raise CLIPEmbeddingError(msg) from e

    async def embed_text(
        self,
        text: str | list[str],
    ) -> list[float] | list[list[float]]:
        """Embed text using CLIP text encoder.

        Args:
            text: Single text string or list of texts

        Returns:
            Embedding vector(s) of dimension 512
        """
        if not self._model or not self._processor:
            msg = "CLIP model not loaded or processor missing"
            raise CLIPEmbeddingError(msg)

        # Ensure list
        is_single = isinstance(text, str)
        texts = [text] if is_single else text

        try:
            # Process text
            inputs = self._processor(
                text=texts,
                return_tensors="pt",
                padding=True,
                truncation=True,
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Get embeddings
            with torch.no_grad():
                text_features = self._model.get_text_features(**inputs)

                # Normalize embeddings
                text_features = text_features / text_features.norm(dim=-1, keepdim=True)

            # Convert to list
            embeddings = text_features.cpu().numpy().tolist()

            # Return single embedding or list
            return embeddings[0] if is_single else embeddings

        except Exception as e:
            msg = f"Failed to embed text: {e}"
            raise CLIPEmbeddingError(msg) from e

    async def embed_image(
        self,
        image: (
            ImageDocument
            | PILImageType
            | str
            | Path
            | list[ImageDocument | PILImageType | str | Path]
        ),
    ) -> list[float] | list[list[float]]:
        """Embed image using CLIP image encoder.

        Args:
            image: ImageDocument, PIL Image, file path, or list of any

        Returns:
            Embedding vector(s) of dimension 512
        """
        if not self._model or not self._processor:
            msg = "CLIP model not loaded or processor missing"
            raise CLIPEmbeddingError(msg)

        # Normalize to a list for processing
        images: list[ImageDocument | PILImageType | str | Path]
        if isinstance(image, list):
            images = image
            is_single = False
        else:
            images = [image]
            is_single = True

        try:
            # Load images
            pil_images = []
            for img in images:
                pil_img = self._load_image(img)
                pil_images.append(pil_img)

            # Process images
            inputs = self._processor(
                images=pil_images,
                return_tensors="pt",
            )
            inputs = {k: v.to(self.device) for k, v in inputs.items()}

            # Get embeddings
            with torch.no_grad():
                image_features = self._model.get_image_features(**inputs)

                # Normalize embeddings
                image_features = image_features / image_features.norm(
                    dim=-1,
                    keepdim=True,
                )

            # Convert to list
            embeddings = image_features.cpu().numpy().tolist()

            # Return single embedding or list
            return embeddings[0] if is_single else embeddings

        except Exception as e:
            msg = f"Failed to embed image: {e}"
            raise CLIPEmbeddingError(msg) from e

    async def embed_batch(
        self,
        texts: list[str] | None = None,
        images: list[ImageDocument | PILImage | str | Path] | None = None,
    ) -> dict:
        """Embed batches of texts and/or images.

        Args:
            texts: Optional list of texts to embed
            images: Optional list of images to embed

        Returns:
            Dictionary with "text_embeddings" and/or "image_embeddings"
        """
        result = {}

        if texts:
            result["text_embeddings"] = await self.embed_text(texts)

        if images:
            result["image_embeddings"] = await self.embed_image(images)

        return result

    def _load_image(
        self,
        image: ImageDocument | PILImageType | str | Path,
    ) -> PILImageType:
        """Load image from various sources.

        Args:
            image: ImageDocument, PIL Image, or file path

        Returns:
            PIL Image
        """
        # Check if it's a PIL Image by checking module and class name
        if (
            hasattr(image, "__class__")
            and image.__class__.__module__.startswith("PIL")
            and image.__class__.__name__ == "Image"
        ):
            return cast("PILImageType", image)

        if isinstance(image, ImageDocument):
            # Load from ImageDocument
            if isinstance(image.content, bytes):
                import io

                return cast("PILImageType", Image.open(io.BytesIO(image.content)))
            return cast("PILImageType", Image.open(image.content))

        if isinstance(image, (str, Path)):
            # Load from file path
            return cast("PILImageType", Image.open(image))

        msg = f"Unsupported image type: {type(image)}"
        raise CLIPEmbeddingError(msg)

    def get_embedding_dimension(self) -> int:
        """Get the dimension of CLIP embeddings.

        Returns:
            Embedding dimension (512 for base model)
        """
        return self._model.config.projection_dim if self._model else 512

    def compute_similarity(
        self,
        embedding1: list[float],
        embedding2: list[float],
    ) -> float:
        """Compute cosine similarity between two embeddings.

        Args:
            embedding1: First embedding vector
            embedding2: Second embedding vector

        Returns:
            Cosine similarity score between -1 and 1
        """
        import numpy as np

        # Convert to numpy arrays
        emb1 = np.array(embedding1)
        emb2 = np.array(embedding2)

        # Compute cosine similarity
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))

        return float(similarity)

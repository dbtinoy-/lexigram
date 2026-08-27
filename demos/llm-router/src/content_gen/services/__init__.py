"""Services — business logic for content generation."""

from __future__ import annotations

from content_gen.services.extractor import ProductExtractor
from content_gen.services.generator import ContentGenerator

__all__ = ["ContentGenerator", "ProductExtractor"]

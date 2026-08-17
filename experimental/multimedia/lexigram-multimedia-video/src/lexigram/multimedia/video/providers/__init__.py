"""Video generation backend providers."""

from __future__ import annotations

from lexigram.multimedia.video.providers.cogvideox import CogVideoXVideoProvider
from lexigram.multimedia.video.providers.comfyui import ComfyUiVideoProvider
from lexigram.multimedia.video.providers.local_http import LocalHttpVideoProvider
from lexigram.multimedia.video.providers.openai import OpenAIVideoProvider
from lexigram.multimedia.video.providers.runway import RunwayVideoProvider
from lexigram.multimedia.video.providers.svd import SVDVideoProvider
from lexigram.multimedia.video.providers.wan22 import Wan22VideoProvider

__all__ = [
    "CogVideoXVideoProvider",
    "ComfyUiVideoProvider",
    "LocalHttpVideoProvider",
    "OpenAIVideoProvider",
    "RunwayVideoProvider",
    "SVDVideoProvider",
    "Wan22VideoProvider",
]

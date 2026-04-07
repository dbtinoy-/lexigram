"""Multimodal enums."""

from __future__ import annotations

from enum import StrEnum


class ImageFormat(StrEnum):
    """Supported image formats."""

    JPEG = "jpeg"
    JPG = "jpg"
    PNG = "png"
    GIF = "gif"
    WEBP = "webp"
    BMP = "bmp"
    TIFF = "tiff"
    SVG = "svg"


class AudioFormat(StrEnum):
    """Supported audio formats."""

    MP3 = "mp3"
    WAV = "wav"
    FLAC = "flac"
    OGG = "ogg"
    AAC = "aac"
    M4A = "m4a"
    WMA = "wma"


class VideoFormat(StrEnum):
    """Supported video formats."""

    MP4 = "mp4"
    AVI = "avi"
    MOV = "mov"
    MKV = "mkv"
    FLV = "flv"
    WMV = "wmv"
    WEBM = "webm"


class Modality(StrEnum):
    """Document modalities."""

    TEXT = "text"
    IMAGE = "image"
    AUDIO = "audio"
    VIDEO = "video"
    MULTIMODAL = "multimodal"

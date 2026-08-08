from dataclasses import dataclass


@dataclass(frozen=True)
class AssetBundle:
    music_path: str | None = None
    font_path: str | None = None
    watermark_path: str | None = None
    bg_clip_path: str | None = None
    outro_clip_path: str | None = None

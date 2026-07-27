import os
import subprocess

import pytest

from shorts_creator.models.asset_bundle import AssetBundle
from shorts_creator.pipeline import pipeline as pmod


def _has_ffmpeg() -> bool:
    try:
        return pmod.subprocess.run(["ffmpeg", "-version"], capture_output=True).returncode == 0
    except FileNotFoundError:
        return False


HAS_FFMPEG = _has_ffmpeg()
SKIP_NO_FFMPEG = pytest.mark.skipif(not HAS_FFMPEG, reason="ffmpeg missing")


def test_generate_outro_clip_accepts_configured_text(tmp_path, monkeypatch):
    def fake_run(argv, **kwargs):
        pass

    png_paths = []

    def fake_unlink(path):
        png_paths.append(path)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(pmod.os, "unlink", fake_unlink)

    out = str(tmp_path / "outro.mp4")
    captured = {}
    monkeypatch.setattr(pmod.subprocess, "run", lambda argv, **kwargs: captured.update(argv=argv))
    pmod.generate_outro_clip(out, 640, 640, text="Custom outro text")

    assert captured["argv"][0] == "ffmpeg"
    assert captured["argv"][-1] == out
    assert captured["argv"][captured["argv"].index("-t") + 1] == str(pmod.OUTRO_DEFAULT_SECONDS)
    assert len(png_paths) == 1 and png_paths[0].endswith(".png")

    from PIL import Image

    def white_count(path):
        return sum(1 for px in Image.open(path).getdata() if px == (255, 255, 255))

    short_png = png_paths[0]
    out2 = str(tmp_path / "outro2.mp4")
    png_paths.clear()
    pmod.generate_outro_clip(out2, 640, 640)
    assert white_count(png_paths[0]) < white_count(short_png)


class TestFontThreading:
    def test_bold_font_uses_custom_path(self, tmp_path, monkeypatch):
        real = pmod.ImageFont.truetype
        calls = []

        def fake_truetype(path, size):
            calls.append(path)
            if os.path.exists(path):
                return real(path, size)
            return real("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", size)

        monkeypatch.setattr(pmod.ImageFont, "truetype", fake_truetype)
        font = pmod._bold_font(48, path="/tmp/custom.ttf")
        assert font is not None
        assert "/tmp/custom.ttf" in calls

    def test_bold_font_defaults_to_dejavu(self):
        font = pmod._bold_font(24)
        assert font is not None


class TestWatermarkBake:
    @SKIP_NO_FFMPEG
    def test_bake_watermark_writes_clip(self, tmp_path):
        wm_path = str(tmp_path / "wm.png")
        pmod.Image.new("RGBA", (64, 64), (255, 0, 0)).save(wm_path)
        out = str(tmp_path / "watermark.mov")
        pmod._render_watermark_clip(wm_path, out, total_frames=60, fps=30.0)
        assert os.path.exists(out)

    def test_watermark_clip_respects_config_knobs(self, tmp_path, monkeypatch):
        from shorts_creator.pipeline.render_config import RenderConfig

        monkeypatch.setattr(pmod.subprocess, "run", lambda *a, **k: None)
        wm_path = str(tmp_path / "wm.png")
        pmod.Image.new("RGBA", (64, 32), (255, 0, 0, 255)).save(wm_path)

        real_resize = pmod.Image.Image.resize
        resizes = []
        monkeypatch.setattr(
            pmod.Image.Image,
            "resize",
            lambda self, size, resample=None, *a, **k: (
                resizes.append(size),
                real_resize(self, size, resample),
            )[1],
        )
        real_paste = pmod.Image.Image.paste
        pastes = []
        monkeypatch.setattr(
            pmod.Image.Image,
            "paste",
            lambda self, im, box=None, mask=None: (
                pastes.append((im, box)),
                real_paste(self, im, box, mask),
            )[1],
        )
        real_point = pmod.Image.Image.point
        points = []
        monkeypatch.setattr(
            pmod.Image.Image,
            "point",
            lambda self, lut, mode=None: (points.append(lut), real_point(self, lut, mode))[1],
        )

        cfg = RenderConfig(
            watermark_size_pct=20.0,
            watermark_opacity=0.4,
            watermark_margin_px=24,
            watermark_corner="top_left",
        )
        pmod._render_watermark_clip(
            wm_path,
            str(tmp_path / "wm.mov"),
            total_frames=60,
            fps=30.0,
            width=1080,
            height=1920,
            render_config=cfg,
        )

        assert resizes[0] == (216, 108)
        assert pastes[0][1] == (24, 24)
        assert points[0](10) == 4  # round(10 * 0.4) via the configured opacity

    def test_bake_music_bed_uses_configured_fade(self, tmp_path, monkeypatch):
        captured = {}
        monkeypatch.setattr(pmod.subprocess, "run", lambda argv, **k: captured.update(argv=argv))
        pmod._bake_music_bed(
            "/tmp/m.wav", str(tmp_path / "bed.wav"), total_seconds=10.0, fade_seconds=3.0
        )
        af = captured["argv"][captured["argv"].index("-af") + 1]
        assert "afade=t=in:d=3" in af
        assert "afade=t=out:st=7.000:d=3" in af


class TestMusicBake:
    @SKIP_NO_FFMPEG
    def test_bake_music_bed_writes_wav(self, tmp_path):
        src = str(tmp_path / "tone.mp3")
        pmod.subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "sine=frequency=440:duration=2",
                "-c:a",
                "libmp3lame",
                src,
            ],
            capture_output=True,
            check=True,
        )
        out = str(tmp_path / "bed.wav")
        pmod._bake_music_bed(src, out, total_seconds=3.0)
        assert os.path.exists(out)


class TestBgClipLoop:
    @SKIP_NO_FFMPEG
    def test_loop_short_clip_to_duration(self, tmp_path):
        src = str(tmp_path / "short.mp4")
        pmod.subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=size=320x240:rate=30",
                "-t",
                "1",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                src,
            ],
            capture_output=True,
            check=True,
        )
        out = str(tmp_path / "looped.mp4")
        pmod._loop_clip_to_duration(src, out, total_seconds=3.5, fps=30.0)
        dur = float(
            pmod.subprocess.run(
                [
                    "ffprobe",
                    "-v",
                    "error",
                    "-show_entries",
                    "format=duration",
                    "-of",
                    "default=noprint_wrappers=1:nokey=1",
                    out,
                ],
                capture_output=True,
                text=True,
                check=True,
            ).stdout.strip()
        )
        assert dur >= 3.4


class TestBackgroundUsesAsset:
    @pytest.mark.asyncio
    @SKIP_NO_FFMPEG
    async def test_fetch_background_uses_asset_clip(self, tmp_path):
        src = str(tmp_path / "bg.mp4")
        pmod.subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=size=320x240:rate=30",
                "-t",
                "1",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                src,
            ],
            capture_output=True,
            check=True,
        )
        pipeline = pmod.ReelPipeline(assets=AssetBundle(bg_clip_path=src))
        pipeline.temp_dir = str(tmp_path)
        result = await pipeline._fetch_background_clip(total_frames=90, fps=30.0)
        assert result == os.path.join(str(tmp_path), "background_asset.mp4")
        assert os.path.exists(result)


class TestBackgroundBundledSample:
    @pytest.mark.asyncio
    @SKIP_NO_FFMPEG
    async def test_fetch_background_uses_bundled_sample_before_stock(self, tmp_path, monkeypatch):
        sample = tmp_path / "sample_nature_asmr.mp4"
        pmod.subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=size=320x240:rate=30",
                "-t",
                "1",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                sample,
            ],
            capture_output=True,
            check=True,
        )
        monkeypatch.setattr(pmod, "SAMPLE_BACKGROUND", sample)
        stock_calls = []

        async def fake_stock(*args, **kwargs):
            stock_calls.append(1)
            return False

        monkeypatch.setattr(pmod.stock_video, "fetch_background_video", fake_stock)
        pipeline = pmod.ReelPipeline()
        pipeline.temp_dir = str(tmp_path)
        result = await pipeline._fetch_background_clip(total_frames=120, fps=30.0)
        assert result == os.path.join(str(tmp_path), "background_sample.mp4")
        assert os.path.exists(result)
        assert stock_calls == []

    @pytest.mark.asyncio
    @SKIP_NO_FFMPEG
    async def test_fetch_background_falls_through_to_stock_without_sample(
        self, tmp_path, monkeypatch
    ):
        monkeypatch.setattr(pmod, "SAMPLE_BACKGROUND", tmp_path / "missing.mp4")
        stock_calls = []

        async def fake_stock(*args, **kwargs):
            stock_calls.append(1)
            return False

        monkeypatch.setattr(pmod.stock_video, "fetch_background_video", fake_stock)
        pipeline = pmod.ReelPipeline()
        pipeline.temp_dir = str(tmp_path)
        result = await pipeline._fetch_background_clip(total_frames=120, fps=30.0)
        assert stock_calls == [1]
        assert result == os.path.join(str(tmp_path), "background_fallback.mp4")
        assert os.path.exists(result)


class TestBackgroundImageMode:
    @pytest.mark.asyncio
    @SKIP_NO_FFMPEG
    async def test_image_mode_loops_user_image_and_skips_stock(self, tmp_path, monkeypatch):
        src = str(tmp_path / "bg.png")
        pmod.subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=red:s=64x64", "-frames:v", "1", src],
            capture_output=True,
            check=True,
        )
        monkeypatch.setattr(pmod, "SAMPLE_BACKGROUND", tmp_path / "missing.mp4")
        stock_calls = []

        async def fake_stock(*args, **kwargs):
            stock_calls.append(1)
            return False

        monkeypatch.setattr(pmod.stock_video, "fetch_background_video", fake_stock)
        pipeline = pmod.ReelPipeline(assets=AssetBundle(bg_clip_path=src), bg_mode="image")
        pipeline.temp_dir = str(tmp_path)
        result = await pipeline._fetch_background_clip(total_frames=90, fps=30.0)
        assert result == os.path.join(str(tmp_path), "background_image.mp4")
        assert os.path.exists(result)
        assert stock_calls == []

    @pytest.mark.asyncio
    @SKIP_NO_FFMPEG
    async def test_image_mode_uses_gradient_without_user_image(self, tmp_path, monkeypatch):
        monkeypatch.setattr(pmod, "SAMPLE_BACKGROUND", tmp_path / "missing.mp4")
        stock_calls = []

        async def fake_stock(*args, **kwargs):
            stock_calls.append(1)
            return False

        monkeypatch.setattr(pmod.stock_video, "fetch_background_video", fake_stock)
        pipeline = pmod.ReelPipeline(bg_mode="image")
        pipeline.temp_dir = str(tmp_path)
        result = await pipeline._fetch_background_clip(total_frames=90, fps=30.0)
        assert stock_calls == []
        assert result == os.path.join(str(tmp_path), "background_fallback.mp4")
        assert os.path.exists(result)

    @pytest.mark.asyncio
    @SKIP_NO_FFMPEG
    async def test_image_mode_user_image_failure_falls_back_to_gradient(
        self, tmp_path, monkeypatch
    ):
        src = str(tmp_path / "bg.png")
        pmod.subprocess.run(
            ["ffmpeg", "-y", "-f", "lavfi", "-i", "color=c=red:s=64x64", "-frames:v", "1", src],
            capture_output=True,
            check=True,
        )

        def fake_loop_image(*args, **kwargs):
            raise subprocess.CalledProcessError(1, "ffmpeg")

        monkeypatch.setattr(pmod, "_looped_image_video", fake_loop_image)
        pipeline = pmod.ReelPipeline(assets=AssetBundle(bg_clip_path=src), bg_mode="image")
        pipeline.temp_dir = str(tmp_path)
        result = await pipeline._fetch_background_clip(total_frames=90, fps=30.0)
        assert result == os.path.join(str(tmp_path), "background_fallback.mp4")
        assert os.path.exists(result)


class TestBackgroundApiSource:
    @pytest.mark.asyncio
    @SKIP_NO_FFMPEG
    async def test_api_source_skips_asset_and_sample_and_pins_provider(self, tmp_path, monkeypatch):
        src = str(tmp_path / "bg.mp4")
        pmod.subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-f",
                "lavfi",
                "-i",
                "testsrc=size=320x240:rate=30",
                "-t",
                "1",
                "-c:v",
                "libx264",
                "-pix_fmt",
                "yuv420p",
                src,
            ],
            capture_output=True,
            check=True,
        )
        monkeypatch.setattr(pmod, "SAMPLE_BACKGROUND", tmp_path / "missing.mp4")
        loop_calls = []
        stock_kwargs = {}

        def fake_loop(*args, **kwargs):
            loop_calls.append(1)
            raise subprocess.CalledProcessError(1, "ffmpeg")

        async def fake_stock(*args, **kwargs):
            stock_kwargs.update(kwargs)
            return False

        monkeypatch.setattr(pmod, "_loop_clip_to_duration", fake_loop)
        monkeypatch.setattr(pmod.stock_video, "fetch_background_video", fake_stock)
        pipeline = pmod.ReelPipeline(
            assets=AssetBundle(bg_clip_path=src),
            bg_source="api",
            stock_provider="pexels",
        )
        pipeline.temp_dir = str(tmp_path)
        result = await pipeline._fetch_background_clip(total_frames=120, fps=30.0)
        assert loop_calls == []
        assert stock_kwargs["provider"] == "pexels"
        assert result == os.path.join(str(tmp_path), "background_fallback.mp4")
        assert os.path.exists(result)

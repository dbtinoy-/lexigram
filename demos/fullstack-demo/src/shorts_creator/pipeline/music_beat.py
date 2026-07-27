"""music_beat pipeline stage - beat-locked looped music bed (design spec §6).

Analyzes the resolved music asset via lexigram-multimedia-beat's in-process
librosa provider, then bakes the bed with:

1. a loop phase offset (adelay) chosen so item 1's first spoken word lands
   on a detected beat (snap <= half beat period),
2. one-pass energy automation (a single `volume` filter with
   `enable=between(t, ...)` windows): duck to ~0.12 under narration, +0.15
   swell on each item boundary that hits a beat, +0.2 swell under the outro,
3. an outro swell region snapped to the nearest beat after narration ends
   (+-0.6s window).

Any failure upstream (missing asset, unanalyzable audio, provider errors)
falls back to the plain looped 0.2 bed - beat features degrade gracefully,
never crash a render. All math is in pure helpers so unit tests exercise it
without executing ffmpeg.
"""

from __future__ import annotations

import subprocess

# Final layer volume stays 0.2 (compose ComposeAudioLayer), so the baked wav
# carries multiplicative factors: 0.12 / 0.2 = 0.6 etc.
DUCK_FACTOR = 0.6
SWELL_FACTOR = 1.35
OUTRO_FACTOR = 2.0
SWELL_WINDOW = 0.6
SNAP_WINDOW = 0.6
FADE_SECONDS = 2.0


def snap_loop_offset(beats: list[float], loop_seconds: float, target_seconds: float) -> float:
    """Return the adelay offset so a detected beat lands on `target_seconds`.

    The looped bed plays `beats` once per `loop_seconds`; the nearest beat
    (cyclic distance) is selected and the offset shifts the bed so that beat
    coincides with the target. The snap error is <= half a beat at most, and
    exactly zero for the nearest beat.
    """
    if not beats or loop_seconds <= 0:
        return 0.0
    phase = target_seconds % loop_seconds
    best_b = beats[0] % loop_seconds
    best_err = float("inf")
    for beat in beats:
        b = beat % loop_seconds
        err = min(abs(b - phase), loop_seconds - abs(b - phase))
        if err < best_err:
            best_b, best_err = b, err
    return round((phase - best_b) % loop_seconds, 3)


def swell_windows(
    boundaries: list[float],
    beats: list[float],
    period: float,
    window: float = SWELL_WINDOW,
) -> list[tuple[float, float]]:
    """(start, end) swells for item boundaries that snap to a detected beat.

    A boundary qualifies when its nearest beat (cyclic on `period`) is within
    half a beat period; the swell window is centered on the snapped beat.
    """
    if not beats or period <= 0:
        return []
    windows = []
    for boundary in boundaries:
        nearest = min(beats, key=lambda b: min(abs(b - boundary), period - abs(b - boundary)))
        err = min(abs(nearest - boundary), period - abs(nearest - boundary))
        if err <= period / 2:
            windows.append((round(nearest, 3), round(nearest + window, 3)))
    return windows


def snap_outro_start(
    beats: list[float],
    narration_end: float,
    window: float = SNAP_WINDOW,
) -> float:
    """Nearest beat to narration_end within the snap window, else narration_end."""
    candidates = [b for b in beats if narration_end - window <= b <= narration_end + window]
    if not candidates:
        return narration_end
    return min(candidates, key=lambda b: abs(b - narration_end))


def build_volume_expression(
    narration_end: float,
    swells: list[tuple[float, float]],
    outro_start: float,
    total_seconds: float,
) -> str:
    """Nested `if(between(t, ...))` chain of multiplicative bed factors.

    The plain bed plays at 1.0; the expression ducks to DUCK_FACTOR under
    narration, swells on item-boundary beats, and lifts to OUTRO_FACTOR under
    the outro. Swells are checked before the narration window (they live
    inside it); the outro region is disjoint and outermost.
    """
    expression = "1"
    expression = f"if(between(t,0,{narration_end:.3f}),{DUCK_FACTOR},{expression})"
    for start, end in swells:
        expression = f"if(between(t,{start:.3f},{end:.3f}),{SWELL_FACTOR},{expression})"
    if outro_start < total_seconds:
        expression = (
            f"if(between(t,{outro_start:.3f},{total_seconds:.3f}),{OUTRO_FACTOR},{expression})"
        )
    return expression


def bake_beat_bed(
    music_path: str,
    out_path: str,
    loop_seconds: float,
    beats: list[float],
    item_starts: list[float],
    narration_end: float,
    total_seconds: float,
    fade_seconds: float = FADE_SECONDS,
) -> None:
    """Bake the beat-locked bed: phase offset + fades + energy automation.

    Raises:
        ValueError: when no beats were detected (callers fall back to the
            plain bed rather than crashing the render).
    """
    if not beats or loop_seconds <= 0:
        raise ValueError("beat bake requires detected beats")
    offset = snap_loop_offset(beats, loop_seconds, item_starts[0])
    swells = swell_windows(item_starts, beats, loop_seconds)
    outro_start = snap_outro_start(beats, narration_end)
    expression = build_volume_expression(narration_end, swells, outro_start, total_seconds)
    fade_out_start = max(0.0, total_seconds - fade_seconds)
    subprocess.run(
        [
            "ffmpeg",
            "-y",
            "-stream_loop",
            "-1",
            "-i",
            music_path,
            "-t",
            f"{total_seconds:.3f}",
            "-af",
            (
                f"adelay={round(offset * 1000)}:all=1,"
                f"afade=t=in:d={fade_seconds},afade=t=out:st={fade_out_start:.3f}:d={fade_seconds},"
                f"volume='{expression}':eval=frame"
            ),
            "-ac",
            "2",
            "-ar",
            "44100",
            "-c:a",
            "pcm_s16le",
            out_path,
        ],
        capture_output=True,
        check=True,
    )


def build_beat_provider():
    """Construct the in-process librosa beat provider, or None when the
    lexigram-multimedia-beat package is unavailable (local dev without the
    container installs it; absent here `music_beat` degrades to the plain
    bed, never raising at import time)."""
    try:
        from lexigram.multimedia.beat.providers.librosa import (
            LibrosaBeatAnalysisProvider,
        )
    except ImportError:
        return None
    return LibrosaBeatAnalysisProvider()

from shorts_creator.pipeline.music_beat import (
    DUCK_FACTOR,
    OUTRO_FACTOR,
    SWELL_FACTOR,
    bake_beat_bed,
    build_volume_expression,
    snap_loop_offset,
    snap_outro_start,
    swell_windows,
)


class TestSnapLoopOffset:
    def test_offset_lands_a_beat_on_target(self):
        beats = [0.5, 1.0, 1.5]
        offset = snap_loop_offset(beats, loop_seconds=4.0, target_seconds=3.2)
        assert (0.5 + offset) % 4.0 == 3.2
        assert offset == 2.7

    def test_offset_is_nearest_beat_within_half_period(self):
        beats = [0.0, 1.0, 2.0, 3.0]
        offset = snap_loop_offset(beats, loop_seconds=4.0, target_seconds=3.05)
        assert offset == 0.05

    def test_empty_beats_returns_zero(self):
        assert snap_loop_offset([], loop_seconds=4.0, target_seconds=3.0) == 0.0


class TestSwellWindows:
    def test_boundary_hitting_a_beat_gets_window(self):
        beats = [0.0, 1.0, 2.0, 3.0, 4.0]
        windows = swell_windows([3.05], beats, period=4.0)
        assert windows == [(3.0, 3.6)]

    def test_boundary_snaps_to_nearest_cyclic_beat(self):
        beats = [0.0, 1.0, 2.0, 3.0, 4.0]
        windows = swell_windows([3.5], beats, period=4.0)
        assert windows == [(0.0, 0.6)]

    def test_multiple_boundaries_produce_multiple_windows(self):
        beats = [0.0, 1.0, 2.0, 3.0, 4.0]
        windows = swell_windows([1.0, 3.0], beats, period=4.0)
        assert windows == [(1.0, 1.6), (3.0, 3.6)]


class TestSnapOutroStart:
    def test_snaps_to_nearest_beat_within_window(self):
        beats = [10.0, 15.0, 20.0]
        assert snap_outro_start(beats, narration_end=15.4) == 15.0

    def test_keeps_narration_end_when_no_beat_in_window(self):
        beats = [10.0, 20.0]
        assert snap_outro_start(beats, narration_end=15.4) == 15.4


class TestBuildVolumeExpression:
    def test_duck_under_narration(self):
        expr = build_volume_expression(
            narration_end=10.0, swells=[], outro_start=10.0, total_seconds=13.0
        )
        assert (
            expr == f"if(between(t,10.000,13.000),{OUTRO_FACTOR},"
            f"if(between(t,0,10.000),{DUCK_FACTOR},1))"
        )

    def test_swells_checked_before_narration_duck(self):
        expr = build_volume_expression(
            narration_end=10.0,
            swells=[(3.0, 3.6)],
            outro_start=10.0,
            total_seconds=13.0,
        )
        swell_pos = expr.find(f"between(t,3.000,3.600),{SWELL_FACTOR}")
        duck_pos = expr.find(f"between(t,0,10.000),{DUCK_FACTOR}")
        assert swell_pos != -1
        assert swell_pos < duck_pos

    def test_outro_lift_present(self):
        expr = build_volume_expression(
            narration_end=10.0, swells=[], outro_start=10.0, total_seconds=13.0
        )
        assert f"between(t,10.000,13.000),{OUTRO_FACTOR}" in expr


def test_bake_beat_bed_uses_configured_fade(tmp_path, monkeypatch):
    captured = {}
    monkeypatch.setattr(
        "shorts_creator.pipeline.music_beat.subprocess.run",
        lambda argv, **kwargs: captured.update(argv=argv),
    )
    bake_beat_bed(
        "/tmp/m.wav",
        str(tmp_path / "bed.wav"),
        loop_seconds=4.0,
        beats=[1.0],
        item_starts=[3.2],
        narration_end=100.0,
        total_seconds=104.0,
        fade_seconds=4.0,
    )
    af = captured["argv"][captured["argv"].index("-af") + 1]
    assert "afade=t=in:d=4.0" in af
    assert "afade=t=out:st=100.000:d=4.0" in af

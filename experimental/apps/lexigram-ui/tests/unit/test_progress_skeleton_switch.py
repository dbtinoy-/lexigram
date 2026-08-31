"""Tests for ProgressBar, Skeleton, and Switch atoms."""

from __future__ import annotations

from lexigram.ui.atoms.progress_bar import ProgressBar
from lexigram.ui.atoms.skeleton import Skeleton
from lexigram.ui.atoms.switch import Switch


class TestProgressBar:
    def test_progress_bar_renders(self) -> None:
        result = str(ProgressBar(value=50))
        assert "50%" in result

    def test_progress_bar_zero(self) -> None:
        result = str(ProgressBar(value=0))
        assert "0%" in result

    def test_progress_bar_full(self) -> None:
        result = str(ProgressBar(value=100))
        assert "100%" in result

    def test_progress_bar_with_label(self) -> None:
        result = str(ProgressBar(value=30, label="Upload progress"))
        assert "Upload progress" in result

    def test_progress_bar_custom_color(self) -> None:
        result = str(ProgressBar(value=60, color="green"))
        assert "bg-primary" in result

    def test_progress_bar_no_percentage_when_disabled(self) -> None:
        result = str(ProgressBar(value=40, show_percentage=False))
        assert "40%" in result

    def test_progress_bar_size_sm(self) -> None:
        result = str(ProgressBar(value=10, size="sm"))
        assert "h-1" in result

    def test_progress_bar_size_lg(self) -> None:
        result = str(ProgressBar(value=10, size="lg"))
        assert "h-3" in result

    def test_progress_bar_role(self) -> None:
        html = str(ProgressBar(value=60))
        assert 'role="progressbar"' in html
        assert 'aria-valuenow="60"' in html
        assert 'aria-valuemin="0"' in html
        assert 'aria-valuemax="100"' in html


class TestSkeleton:
    def test_skeleton_text_variant_renders(self) -> None:
        result = str(Skeleton())
        assert "animate-pulse" in result

    def test_skeleton_circular_variant(self) -> None:
        result = str(Skeleton(variant="circular"))
        assert "rounded-full" in result

    def test_skeleton_rectangular_variant(self) -> None:
        result = str(Skeleton(variant="rectangular"))
        assert "animate-pulse" in result
        assert "rounded-full" not in result

    def test_skeleton_text_multiple_lines(self) -> None:
        result = str(Skeleton(variant="text", count=3))
        assert result.count("animate-pulse") == 3

    def test_skeleton_text_last_line_shorter(self) -> None:
        result = str(Skeleton(variant="text", count=2))
        assert "80%" in result

    def test_skeleton_shadcn_parity(self) -> None:
        html = str(Skeleton())
        assert "animate-pulse" in html
        assert "rounded-md" in html
        assert "bg-muted" in html


class TestSwitch:
    def test_switch_renders(self) -> None:
        result = str(Switch(label="Enable notifications", name="notifications"))
        assert "Enable notifications" in result

    def test_switch_name_in_output(self) -> None:
        result = str(Switch(label="Dark mode", name="dark_mode"))
        assert "dark_mode" in result

    def test_switch_with_error_is_associated_with_the_control(self) -> None:
        result = str(Switch(label="Accept", name="accept", error="Required field"))
        assert "Required field" in result
        assert 'id="accept-error"' in result
        assert 'aria-invalid="true"' in result
        assert 'aria-describedby="accept-error"' in result

    def test_switch_disables_both_visual_and_submitted_controls(self) -> None:
        result = str(Switch(label="Accept", name="accept", disabled=True))
        assert result.count("disabled") >= 2

    def test_switch_checked_state(self) -> None:
        result = str(Switch(label="Active", name="active", value=True))
        assert "Active" in result

    def test_switch_shadcn_parity(self) -> None:
        html = str(Switch(label="s", name="s"))
        assert "h-6 w-11" in html
        assert "rounded-full border-2 border-transparent" in html
        assert (
            "focus-visible:ring-2 focus-visible:ring-ring focus-visible:ring-offset-2"
            in html
        )

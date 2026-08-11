"""Daily Success Mindset — Short-form Reel Pipeline.

Orchestrates end-to-end reel creation: LLM script generation, TTS narration,
stock video sourcing, caption rendering, and ffmpeg compose render.
"""

import time
from typing import TextIO

_PIPELINE_START = time.time()
_LOG_TEES: dict[int, TextIO] = {}


def add_log_tee(stream: TextIO) -> None:
    """Register an extra write target for pipeline stage traces.

    Unlike a global ``redirect_stdout``, this only tees the pipeline's own
    ``_log`` output. Concurrent renders each register their own stream, so
    sys.stdout is never swapped process-wide and other requests keep logging
    normally.
    """
    _LOG_TEES[id(stream)] = stream


def remove_log_tee(stream: TextIO) -> None:
    _LOG_TEES.pop(id(stream), None)


def _log(msg: str) -> None:
    """Print with an elapsed-since-start prefix so a live-tailed log shows
    exactly when each stage ran and how long gaps between them were -
    needed to tell "still working" apart from "stuck" during a run.
    """
    line = f"[{time.time() - _PIPELINE_START:7.1f}s] {msg}"
    print(line)
    for stream in list(_LOG_TEES.values()):
        try:
            stream.write(line + "\n")
        except (ValueError, OSError):  # tee closed mid-run; logging is best-effort
            pass

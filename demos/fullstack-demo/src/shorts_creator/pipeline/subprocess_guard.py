"""Registry of live pipeline subprocesses so the watchdog can kill them.

The pipeline runs blocking children (chatterbox, whisper, ffmpeg) inside
executor threads; cancelling the asyncio task does NOT stop those threads,
so a hung child would keep running after the run was failed. Every child is
spawned with start_new_session=True and registered here keyed by the run it
belongs to; kill_all(owner) sends SIGKILL to just that run's process groups
(children included), so one run's watchdog can never murder another run's
live subprocesses.
"""

import os
import signal
import subprocess
import threading
from collections import defaultdict
from typing import Any

_ACTIVE: dict[str, set[subprocess.Popen]] = defaultdict(set)
_LOCK = threading.Lock()


def spawn(cmd: list[str], owner: str = "", **kwargs: Any) -> subprocess.Popen:
    """Start a registered, group-leader subprocess (or raise)."""
    proc = subprocess.Popen(cmd, start_new_session=True, **kwargs)
    with _LOCK:
        _ACTIVE[owner].add(proc)
    return proc


def active_procs(owner: str = "") -> set[subprocess.Popen]:
    with _LOCK:
        return set(_ACTIVE.get(owner, ()))


def done(proc: subprocess.Popen) -> None:
    with _LOCK:
        for owner in list(_ACTIVE):
            group = _ACTIVE[owner]
            group.discard(proc)
            if not group:
                del _ACTIVE[owner]


def kill_all(owner: str | None = None) -> int:
    """SIGKILL live process groups. With no argument, everything; with an
    owner, only that owner's groups. Returns how many were signalled."""
    with _LOCK:
        if owner is not None:
            procs = list(_ACTIVE.get(owner, ()))
            _ACTIVE.pop(owner, None)
        else:
            procs = [p for group in _ACTIVE.values() for p in group]
            _ACTIVE.clear()
    killed = 0
    for proc in procs:
        try:
            if proc.poll() is None:
                os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                killed += 1
        except (ProcessLookupError, PermissionError, OSError):
            pass
    return killed


def kill(proc: subprocess.Popen) -> None:
    try:
        if proc.poll() is None:
            os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
    except (ProcessLookupError, PermissionError, OSError):
        pass
    done(proc)


def run_blocking(
    cmd: list[str], *, owner: str = "", input: str | None = None, timeout: int, label: str
) -> subprocess.CompletedProcess:
    """Run `cmd` as a registered process group with a hard timeout.

    On timeout the whole process group is SIGKILLed (not just the direct
    child - torch/ffmpeg spawn helpers that keep the pipes open and would
    otherwise hang communicate() forever). Failure messages include the
    tail of the child's stderr so the UI shows the real cause.
    """
    proc = spawn(
        cmd,
        owner=owner,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    try:
        out, err = proc.communicate(input=input, timeout=timeout)
        done(proc)
    except subprocess.TimeoutExpired:
        kill(proc)
        raise RuntimeError(f"{label} timed out after {timeout}s and was killed") from None
    if proc.returncode != 0:
        tail = (err or "").strip().splitlines()[-5:]
        raise RuntimeError(f"{label} failed (exit {proc.returncode}): {' | '.join(tail)}")
    return subprocess.CompletedProcess(proc.args, 0, stdout=out, stderr=err)

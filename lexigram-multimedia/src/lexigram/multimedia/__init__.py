"""Lexigram Multimedia — generation umbrella package.

Install `lexigram-multimedia` to get the full multimedia subsystem.
Import from sub-packages for granular control.
"""

from __future__ import annotations

import pkgutil

# Critical: enable namespace-package discovery for lexigram.multimedia.*
# sibling distributions (audio_tts, audio_music, video, image).
__path__ = pkgutil.extend_path(__path__, __name__)

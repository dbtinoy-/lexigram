---
name: narrated
label: Narrated
description: Spoken narration with on-screen captions that track the narration.
caption_styles:
  - highlight
  - plain
default_caption_style: highlight
duration_range: [38, 50]
pacing_wps_range: [2.5, 3.0]
requires:
  script: [hook]
  voice: [tts_story]
  pipeline: [tts_story, word_timing, captions, background, outro, music_beat]
layout:
  anchor: center
  block_width_pct: [60, 95]
  numbered_scale: [1.2, 2.5]
  pill_per_word: true
palette:
  highlight_colour: 0x7C5CFAFF
  pill_bg_colour: 0x000000C0
defaults:
  caption_font_size: 56
  music_volume: 0.2
  loudness_target_lufs: -14
  audio_normalize: true
objectives: []
assets: []
---
---
name: steps
label: Steps
description: Numbered checklist steps with a final check-in screen; minimal narration.
caption_styles: []
default_caption_style: ""
duration_range: [38, 50]
pacing_wps_range: [2.5, 3.0]
requires:
  script: [hook, top_items]
  voice: [tts_story]
  pipeline: [tts_story, word_timing, captions, background, music_beat, outro]
layout:
  anchor: center
  block_width_pct: [60, 95]
  numbered_scale: [1.2, 2.5]
  pill_per_word: true
palette:
  highlight_colour: 0x7C5CFAFF
  pill_bg_colour: 0x000000C0
defaults:
  ranked_number_scale: 1.4
objectives: []
assets: []
---
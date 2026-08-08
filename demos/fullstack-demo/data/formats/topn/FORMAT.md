---
name: topn
label: Top N
description: A ranked list of 5 concrete items for the topic, each shown on its own numbered screen, driven by a beat-locked music bed.
caption_styles: []
default_caption_style: ""
duration_range: [35, 50]
pacing_wps_range: [2.4, 3.0]
requires:
  script: [hook, top_items, conclusion]
  voice: [tts_story]
  pipeline: [tts_story, word_timing, background, ranked_screens, outro, music_beat]
  assets: [music]
layout:
  anchor: center
  block_width_pct: [60, 95]
  numbered_scale: [1.2, 2.5]
  pill_per_word: true
palette:
  highlight_colour: 0x7C5CFAFF
  pill_bg_colour: 0x000000C0
defaults: {music_volume: 0.2, loudness_target_lufs: -14, audio_normalize: true}
objectives: []
---
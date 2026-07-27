---
name: myth
label: Myth vs Fact
description: A claim, three correcting facts, and a reframing twist with stage accents.
caption_styles: [highlight, plain]
default_caption_style: plain
duration_range: [38, 50]
pacing_wps_range: [2.5, 3.0]
requires:
  script: [hook, claim, fact, twist]
  voice: [tts_story]
  pipeline: [tts_story, word_timing, captions, background, outro]
layout:
  anchor: center
  block_width_pct: [60, 95]
  numbered_scale: [1.2, 2.5]
  pill_per_word: true
palette:
  highlight_colour: 0x7C5CFAFF
  pill_bg_colour: 0x000000C0
defaults:
  stage_accents: {}
objectives: []
assets: []
---
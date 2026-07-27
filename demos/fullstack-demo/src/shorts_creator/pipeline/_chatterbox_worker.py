"""Batch Chatterbox TTS worker, run in chatterbox-venv (see narration.py).

Loads the model once, then synthesizes every line in the batch - reloading
a multi-GB model per line would dominate runtime. Takes a JSON array of
{"text": str, "out_wav": str, "exaggeration": float, "cfg_weight": float,
"temperature": float} on stdin, writes one WAV per item. Items may omit
the prosody keys; the constants below (the "natural" preset, see
narration.VOICE_PRESETS) then apply.
"""

import json
import sys

import torch
import torchaudio as ta
from chatterbox.tts import ChatterboxTTS

# Chatterbox's single built-in voice. These are the "general use" defaults
# from narration.VOICE_PRESETS["natural"]: Chatterbox's documented
# "expressive/dramatic" combination (exaggeration 0.7 / cfg_weight 0.3)
# pushes prosody hard enough to read as strained/robotic on this voice
# rather than human. Temperature is nudged up slightly from Chatterbox's
# default (0.8) for a bit more natural pitch/pacing variation between lines
# instead of a flat, uniform delivery, without going high enough to risk
# mispronunciations. narration.synthesize_batch always sends explicit
# values per item, so these only apply to hand-written test batches.
EXAGGERATION = 0.5
CFG_WEIGHT = 0.5
TEMPERATURE = 0.85


def main() -> None:
    items = json.load(sys.stdin)
    device = "cuda" if torch.cuda.is_available() else "cpu"
    model = ChatterboxTTS.from_pretrained(device=device)
    for item in items:
        wav = model.generate(
            item["text"],
            exaggeration=item.get("exaggeration", EXAGGERATION),
            cfg_weight=item.get("cfg_weight", CFG_WEIGHT),
            temperature=item.get("temperature", TEMPERATURE),
        )
        ta.save(item["out_wav"], wav, model.sr)


if __name__ == "__main__":
    main()

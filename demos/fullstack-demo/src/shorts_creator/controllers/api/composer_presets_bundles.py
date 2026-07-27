STARTER_PRESETS = [
    {
        "name": "Fast cuts",
        "payload": {
            "format_name": "narrated",
            "duration_seconds": 38.0,
            "pacing_wps": 2.5,
            "background_motion": "pan",
            "emphasis_style": "scale",
            "loudness_target_lufs": -14.0,
            "audio_normalize": True,
            "section_holds": {"message": -0.5},
            "stage_accents": {"hook": "0xFB7185FF"},
        },
    },
    {
        "name": "Calm narrative",
        "payload": {
            "format_name": "narrated",
            "duration_seconds": 46.0,
            "pacing_wps": 2.5,
            "background_motion": "none",
            "emphasis_style": "off",
            "loudness_target_lufs": -16.0,
            "audio_normalize": True,
            "section_holds": {"hook": 0.5, "message": 0.8, "conclusion": 1.5},
            "stage_accents": {"conclusion": "0x34D399FF"},
        },
    },
    {
        "name": "Cinematic",
        "payload": {
            "format_name": "narrated",
            "duration_seconds": 42.0,
            "pacing_wps": 2.7,
            "background_motion": "zoom",
            "emphasis_style": "accent",
            "loudness_target_lufs": -12.0,
            "audio_normalize": True,
            "section_holds": {"hook": 0.4, "conclusion": 1.2},
            "stage_accents": {"hook": "0x7C5CFAFF", "conclusion": "0x22D3EEFF"},
        },
    },
]

# lexigram-multimedia

Multimedia generation umbrella for the Lexigram Framework — text-to-speech,
music, video, and image generation behind one `MultimediaProvider`.

Discovers its subsystem packages (`audio-tts`, `audio-music`, `video`,
`image`) via `lexigram.multimedia.subsystems` entry points, normalizes
assets into blob storage, and submits generation jobs to the task queue.

See the individual packages for standalone use:
`lexigram-multimedia-audio-tts`, `lexigram-multimedia-audio-music`,
`lexigram-multimedia-video`, `lexigram-multimedia-image`.

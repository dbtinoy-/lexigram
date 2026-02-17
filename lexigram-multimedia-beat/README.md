# lexigram-multimedia-beat

Audio tempo/beat analysis for the Lexigram Framework — analyzes an
audio `MediaAsset` and returns tempo (BPM) and beat timestamps, for
driving beat-synced cut timing in a calling application.

Two backends: `librosa` (default, runs in-process, no reference
server) and `madmom` (optional, deep-learning-based, reference-server
pattern — better on syncopated or tempo-changing material).

Part of the `lexigram-multimedia` package family. See the umbrella
package `lexigram-multimedia` for orchestration, or use this package
directly via `BeatAnalysisModule.configure(...)`.

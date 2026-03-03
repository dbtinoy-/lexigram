# lexigram-ai-relay

Protocol-neutral conversion engine for the Lexigram AI relay.

Converts between OpenAI Chat Completions, OpenAI Responses, Anthropic
Messages, and Gemini generateContent wire formats through one canonical
intermediate representation.

The engine is synchronous and side-effect free: it never performs HTTP,
channel selection, billing, or model selection. Host capabilities
(Claude default `max_tokens`, Gemini safety thresholds, media
resolution, model suffixes) are supplied as typed callbacks through
`RelayConversionContext` from `lexigram-contracts`.

import io

from lexigram.contracts.ai.llm import ChatMessage, Role

FALLBACK_TARGET_SIZE = 4
HOOK_LINE_TARGET_SIZE = 1

_GROUP_PROMPT = """Split the TRANSCRIPT below into short phrase groups for on-screen video captions.

Rules:
- Each group must be 3 to 5 words (a group of 1-2 words is only OK for a final leftover fragment).
- Never split in the middle of a natural phrase - keep words that belong together grammatically in the same group.
- Use the EXACT words, word order, and punctuation from the TRANSCRIPT below. Do not add, remove, or reword anything.
- Separate groups with " | " and output nothing else - no explanation, no numbering, no quotes.

For context, this transcript is a spoken rendition of: {line}

TRANSCRIPT: {transcript}"""


async def group_by_thought(line: str, words: list[dict], llm) -> list[list[dict]]:
    if not words:
        return []
    transcript = " ".join(w["word"] for w in words)
    sizes = await _thought_group_sizes(line, transcript, len(words), llm)
    if sizes is None:
        sizes = _fallback_sizes(words, FALLBACK_TARGET_SIZE)
    return _sizes_to_chunks(words, sizes)


def group_for_hook_display(
    words: list[dict], target_size: int = HOOK_LINE_TARGET_SIZE
) -> list[list[dict]]:
    if not words:
        return []
    sizes = _fallback_sizes(words, target_size)
    return _sizes_to_chunks(words, sizes)


def _sizes_to_chunks(words: list[dict], sizes: list[int]) -> list[list[dict]]:
    chunks = []
    idx = 0
    for size in sizes:
        chunks.append(words[idx : idx + size])
        idx += size
    return chunks


async def _thought_group_sizes(
    line: str, transcript: str, word_count: int, llm
) -> list[int] | None:
    prompt = _GROUP_PROMPT.format(line=line, transcript=transcript)
    try:
        result = await llm.complete(
            messages=[ChatMessage(role=Role.USER, content=prompt)], model=""
        )
        if result.is_err():
            return None
        response = result.unwrap().content
    except Exception:  # noqa: BLE001 - LLM failure degrades to default chunking
        return None
    groups = [g.strip() for g in response.split("|") if g.strip()]
    sizes = [len(g.split()) for g in groups]
    if sizes and sum(sizes) == word_count:
        return sizes
    return None


def _fallback_sizes(words: list[dict], target: int) -> list[int]:
    sizes = []
    current = 0
    for i, w in enumerate(words):
        current += 1
        is_last = i == len(words) - 1
        ends_clause = w["word"][-1:] in ".,!?" if w["word"] else False
        if is_last or current >= target + 1 or (current >= target - 1 and ends_clause):
            sizes.append(current)
            current = 0
    return sizes


def render_caption_frame_pixels(
    words: list,
    highlighted_idx: int | None = None,
    emphasize: set[str] | None = None,
    render_config=None,
    font_size: int = 64,
) -> bytes:
    from shorts_creator.pipeline.pipeline import _render_caption_frame

    text = [w["word"] if isinstance(w, dict) else w for w in words]
    img = _render_caption_frame(
        text,
        highlighted_idx=highlighted_idx,
        font_size=font_size,
        render_config=render_config,
        emphasize=emphasize,
    )
    buf = io.BytesIO()
    img.save(buf, format="PNG")
    return buf.getvalue()

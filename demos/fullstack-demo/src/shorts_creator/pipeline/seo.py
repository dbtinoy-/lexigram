import asyncio

from lexigram.contracts.ai.llm import ChatMessage, Role

from shorts_creator.topics import ParsedScript

from . import prompts


def _log(msg: str) -> None:
    print(f"   {msg}")


async def research_keywords(focus: str, llm) -> str:
    prompt = prompts.build_keyword_research_prompt(focus=focus)
    try:
        result = await asyncio.wait_for(
            llm.complete(messages=[ChatMessage(role=Role.USER, content=prompt)], model=""),
            timeout=30,
        )
        if result.is_err():
            raise RuntimeError(str(result.unwrap_err()))
        return result.unwrap().content.strip()
    except Exception as exc:  # noqa: BLE001 - research is best-effort; skip on failure
        _log(f"Keyword research skipped ({exc})")
        return ""


async def research_content_angles(title: str, core_message: str, llm) -> str:
    prompt = prompts.build_angle_research_prompt(title=title, core_message=core_message)
    try:
        result = await asyncio.wait_for(
            llm.complete(messages=[ChatMessage(role=Role.USER, content=prompt)], model=""),
            timeout=30,
        )
        if result.is_err():
            raise RuntimeError(str(result.unwrap_err()))
        return result.unwrap().content.strip()
    except Exception as exc:  # noqa: BLE001 - research is best-effort; skip on failure
        _log(f"Content angle research skipped ({exc})")
        return ""


def _format_script_for_seo(script: ParsedScript) -> str:
    parts = [f"Title: {script.title}", f"Duration: {script.total_duration}s"]
    for section in script.sections:
        parts.append(f'{section.name.title()}: "{section.text}"')
    return "\n".join(parts) + "\n"


async def generate_seo_metadata(script: ParsedScript, llm) -> dict:
    prompt = prompts.build_seo_metadata_prompt(
        script_text=_format_script_for_seo(script),
    )
    try:
        result = await asyncio.wait_for(
            llm.complete(messages=[ChatMessage(role=Role.USER, content=prompt)], model=""),
            timeout=30,
        )
        if result.is_err():
            raise RuntimeError(str(result.unwrap_err()))
        raw = result.unwrap().content
    except Exception as exc:  # noqa: BLE001 - metadata is best-effort; skip on failure
        _log(f"SEO metadata generation skipped ({exc})")
        return {}

    SECTION_KEYS = {
        "YOUTUBE_TITLE:": "youtube_title",
        "YOUTUBE_DESCRIPTION:": "youtube_description",
        "YOUTUBE_TAGS:": "youtube_tags",
        "FACEBOOK_CAPTION:": "facebook_caption",
    }

    meta: dict[str, str] = {}
    current_key = ""
    for line in raw.splitlines():
        stripped = line.strip()
        matched = False
        for prefix, key in SECTION_KEYS.items():
            if stripped.startswith(prefix):
                current_key = key
                rest = stripped[len(prefix) :].strip()
                meta[current_key] = rest
                matched = True
                break
        if matched:
            continue
        if current_key:
            if current_key in ("youtube_title", "youtube_tags"):
                if stripped and not meta.get(current_key):
                    meta[current_key] = stripped
                elif stripped:
                    meta[current_key] += " " + stripped
            elif current_key in ("youtube_description", "facebook_caption"):
                if stripped == "":
                    meta[current_key] += "\n"
                else:
                    meta[current_key] += stripped + "\n"

    for k in ("youtube_description", "facebook_caption"):
        if k in meta:
            meta[k] = meta[k].strip()

    return meta
